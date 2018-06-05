import json
import common.psycopg2_functions
import common.nuclio_helper_functions
import nuclio_sdk

MODES_WORTH_PULLING = ['pull']


# get test_case_id & pull_mode in event.body
def handler(context, event):

    # load data from given json,
    run_information = event.body
    pull_mode = run_information.get('pull_mode')
    test_case_id = run_information.get('test_case_id')

    # cur is the cursor of current connection
    cur = context.user_data.conn.cursor()

    # pull tester image
    common.nuclio_helper_functions.run_command(context, f'docker pull localhost:5000/tester:latest-amd64')

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
    context.platform.call_function('test-case-complete',  nuclio_sdk.Event(body={
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



def get_artifact_test_from_test_case(cur, test_case_id):
    cur.execute('select artifact_test from test_cases where oid = %s', (test_case_id,))
    return get_cursors_one_result(cur, f'select artifact_test from test_cases where oid = {test_case_id}')


def _pull_mode_requires_pulling(pull_mode):
    return pull_mode in MODES_WORTH_PULLING


def _run_next_test_case(context, test_case_id, cur):

    artifact_test = get_artifact_test_from_test_case(cur, test_case_id)

    return(common.nuclio_helper_functions.run_command(context, f'docker run --rm --volume /var/run/docker.sock:/var/run/docker.sock '
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
        common.nuclio_helper_functions.run_command(context, f'docker pull {url}')


def _update_test_cases_logs(logs, test_case_id, cur):
    cur.execute('update test_cases set logs=%s where oid=%s;', (logs, test_case_id))


def init_context(context):
    setattr(context.user_data, 'conn', common.psycopg2_functions.get_psycopg2_connection())

