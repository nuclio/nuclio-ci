import psycopg2
import os
import parse
import requests
import json


# event body should contain: git_url, git_commit, git_username, commit_sha, git_branch
def handler(context, event):
    request_body = json.loads(event.body)

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

    # cur is the cursor of current connection
    cur = conn.cursor()

    # create a db job object with information about this job. set the
    # state to building artifacts
    cur.execute('insert into jobs (state) values (1) returning oid')

    # get OID of inserted job
    job_oid = cur.fetchone()[0]

    # notify via slack that build is running
    call_function('slack_notifier', json.dumps({'slack_username': request_body.get('git_username')}))

    # notify via github that build is running
    call_function('github_status_updater', json.dumps({
        'state': 'pending',
        'repo_url': request_body.get('git_url'),
        'commit_sha': request_body.get('commit_sha')
    }))

    # build artifacts. this will clone the git repo and build artifacts.
    artifact_urls = call_function('build_and_push_artifacts', json.dumps({
        'git_url': request_body.get('got_url'),
        'git_commit': request_body.get('git_commit'),
        'git_branch': request_body.get('git_branch')
    }))

    # save artifact URLs in job
    cur.execute(f'update jobs set artifact_urls = \'{artifact_urls}\' where oid = {job_oid}')

    # for each artifact test, create a “test case” object in the database
    for artifact_test in artifact_urls.split(' '):
        cur.execute(f'insert into test_cases (job, artifact_test) values ({job_oid}, \'{artifact_test}\')')

    # check if free nodes selection returns a value, if not -> there are no free nodes, so return
    cur.execute('select oid from nodes where current_test_case = -1')
    if cur.fetchall() is None:
        context.logger.info('No more free nodes, quits.')
        return

    # iterate over the tests of the job
    cur.execute(f'select oid from test_cases where job = {job_oid}')
    for test_case in cur.fetchall():

        # get first value (relevant one) of the returned postgresSql tuple
        test_case = test_case[0]

        # get an idle node
        cur.execute(f'select oid from nodes where current_test_case = -1')

        # if there’s no idle node, we’re done
        idle_node = cur.fetchone()

        if idle_node is None:
            context.logger.info('No more idle_nodes, quits.')
            return

        # get first value (relevant one) of the returned postgresSql tuple
        idle_node = idle_node[0]

        # set the test case running on that node in the db
        cur.execute(f'update nodes set current_test_case = {test_case} where oid={idle_node}')

        # run the specific test case on the specific node. since this is the first time this node will
        # run a test, pull is required
        context.logger.info_with('started test case', Node=idle_node, Test_case_id=test_case)
        # call_function('run_test_case', json.dumps({'node': idle_node,
        #                                            'pull_required': True,
        #                                            'test_case_id': test_case}))


def parse_env_var_info(formatted_string):
    if formatted_string is not None:

        # check if default formatted string given
        if parse.parse('{}:{}@{}:{}', formatted_string) is not None:
            return list(parse.parse('{}:{}@{}:{}', formatted_string))

        # if not, try get same format without the port specification
        if parse.parse('{}:{}@{}', formatted_string) is not None:
            return list(parse.parse('{}:{}@{}', formatted_string)) + [5432]
    return None


# calls given function with given arguments, returns body of response
def call_function(function_name, function_arguments=None):
    functions_ports = {
        'database_init': 36543,
        'github_status_updater': 36544,
        'slack_notifier': 36545,
        'build_and_push_artifacts': 36546,
        'run_test_case': 36547
    }

    # if given_host is specified post it instead of
    given_host = os.environ.get('DOCKER_HOST', '172.17.0.1')
    response = requests.post(f'http://{given_host}:{functions_ports[function_name]}',
                             data=function_arguments)

    return response.text
