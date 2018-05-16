import os
import json
import parse
import requests
import psycopg2
import delegator

MODES_WORTH_PULLING = ['pull']


# get test_case_id & pull_mode in event.body
def handler(context, event):

    # load data from given json,
    run_information = json.loads(event.body)
    pull_mode = run_information.get('pull_mode')
    test_case_id = run_information.get('test_case_id')

    # get a connection to the postgresSql database
    conn = connect_to_db()

    # cur is the cursor of current connection
    cur = conn.cursor()

    # pull tester image
    run_command(context, f'docker pull localhost:5000/tester:latest-amd64')

    if _pull_mode_requires_pulling(pull_mode):
        _pull_images(context, cur, test_case_id)

    # gather logs to a variable
    logs = _run_next_test_case(context, test_case_id, cur)

    # update test_cases values
    _update_test_cases_logs(logs, test_case_id, cur)

    # get run_result from logs
    run_result = get_run_result_from_logs(logs)

    context.logger.info_with('Sending data to test_case_complete', test_case=test_case_id, test_case_result=run_result)
    # call test_case_complete
    call_function('test_case_complete', json.dumps({
        'test_case': test_case_id,
        'test_case_result': 'success' if run_result == '0' else 'failure',
    }))


# gets current cursor and command, alerts if returned 0 values
def get_cursors_one_result(cur, cmd):
    returned_value = cur.fetchone()

    if returned_value is None:
        return Exception(cmd)

    return returned_value[0]


# get run result, ignore empty lines
def get_run_result_from_logs(logs):

    # separate to lines
    run_result = logs.split('\n')

    # filter all empty lines
    run_result = list(filter(lambda x: x, run_result))

    # return last line
    return run_result[-1]


# connect to db, return psycopg2 connection
def connect_to_db():

    # get postgres connection information from container's environment vars
    postgres_info = parse_env_var_info(os.environ.get('PGINFO'))

    # raise NameError if env var not found, or found in wrong format
    if postgres_info is None:
        raise ValueError('Local variable PGINFO in proper format (user:password@host:port or user:password@host)'
                         ' could not be found')

    postgres_user, postgres_password, postgres_host, postgres_port = postgres_info

    # connect to postgres database, set autocommit to True to avoid committing
    conn = psycopg2.connect(host=postgres_host, user=postgres_user, password=postgres_password, port=postgres_port)
    conn.autocommit = True

    return conn


# calls given function with given arguments, returns body of response
def call_function(function_name, function_arguments=None):
    functions_ports = {
        'database_init': 36543,
        'github_status_updater': 36544,
        'slack_notifier': 36545,
        'build_and_push_artifacts': 36546,
        'run_test_case': 36547,
        'test_case_complete': 36549
    }

    # if given_host is specified post it instead of
    given_host = os.environ.get('DOCKER_HOST', '172.17.0.1')
    response = requests.post('http://{0}:{1}'.format(given_host, functions_ports[function_name]),
                             data=function_arguments)

    return response.text


# gets string to process, return None if format is wrong, list of info if format is well writen -
# return-list : username, password, host, port
def parse_env_var_info(formatted_string):
    if formatted_string is not None:

        # check if default formatted string given
        if parse.parse('{}:{}@{}:{}', formatted_string) is not None:
            return list(parse.parse('{}:{}@{}:{}', formatted_string))

        # if not, try get same format without the port specification
        if parse.parse('{}:{}@{}', formatted_string) is not None:
            return list(parse.parse('{}:{}@{}', formatted_string)) + [5432]
    return None


# get env in map format {"key1":"value1"}
def run_command(context, cmd, cwd=None, env=None, accept_error=False):

    context.logger.info_with('Running command', cmd=cmd, cwd=cwd, env=env)

    os_environ_copy = os.environ.copy()

    if env is not None:
        for key in env:
            del os_environ_copy[key]
        env.update(os_environ_copy)
    else:
        env = os_environ_copy

    if cwd is not None:
        cmd = f'cd {cwd} && {cmd}'

    proc = delegator.run(cmd, env=env)

    # if we got here, the process completed
    if not accept_error and proc.return_code != 0:
        raise ValueError(f'Command failed. cmd({cmd}) result({proc.return_code}), log({proc.out})')

    # log result
    if proc.return_code == 0:
        context.logger.info_with('Command executed successfully', Command=cmd, Exit_code=proc.return_code, Stdout=proc.out)
    else:
        context.logger.info_with('Command failed', Command=cmd, Exit_code=proc.return_code, Stdout=proc.out)

    return proc.out


def get_artifact_test_from_test_case(cur, test_case_id):
    cur.execute('select artifact_test from test_cases where oid = %s', (test_case_id,))
    return get_cursors_one_result(cur, f'select artifact_test from test_cases where oid = {test_case_id}')


def _pull_mode_requires_pulling(pull_mode):
    return pull_mode in MODES_WORTH_PULLING


def _run_next_test_case(context, test_case_id, cur):

    artifact_test = get_artifact_test_from_test_case(cur, test_case_id)

    return(run_command(context, f'docker run --rm --volume /var/run/docker.sock:/var/run/docker.sock '
                                f'--volume /tmp:/tmp --workdir /go/src/github.com/nuclio/nuclio --env '
                                f'NUCLIO_TEST_HOST=172.17.0.1 localhost:5000/tester:latest-amd64'
                                f' /bin/bash -c "make test-undockerized '
                                f'NUCLIO_TEST_NAME=github.com/nuclio/nuclio/{artifact_test}" && echo $?',
                       accept_error=True))


# pull images of given test case,
def _pull_images(context, cur, test_case_id):

    # get job's artifact-urls
    cur.execute('select job from test_cases where oid = %s', (test_case_id,))
    jobs_id = get_cursors_one_result(cur, f'select job from test_cases where oid = {test_case_id}')

    # get all artifact url's from job's id
    cur.execute('select artifact_urls from jobs where oid = %s', (jobs_id,))
    artifact_urls = json.loads(get_cursors_one_result(cur, f'select artifact_urls from jobs where oid = {jobs_id}'))

    for url in artifact_urls:
        run_command(context, f'docker pull {url}')


def _update_test_cases_logs(logs, test_case_id, cur):
    cur.execute('update test_cases set logs=%s where oid=%s;', (logs, test_case_id))
