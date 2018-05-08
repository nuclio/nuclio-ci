import psycopg2
import os
import parse
import requests
import json


# event body should contain: git_url, github_username, commit_sha, git_branch, clone_url
def handler(context, event):
    request_body = json.loads(event.body)

    # get a connection to the postgresSql database
    conn = connect_to_db()

    # cur is the cursor of current connection
    cur = conn.cursor()

    # insert job and save its OID
    job_oid = create_job(cur)

    # get slack username
    slack_username = convert_slack_username(cur, request_body.get("github_username"))

    # notify via slack that build is running
    call_function('slack_notifier', json.dumps({
        'slack_username': slack_username,
        'message': 'Your Nuci test started'
    }))

    # notify via github that build is running
    call_function('github_status_updater', json.dumps({
        'state': 'pending',
        'repo_url': request_body.get('git_url'),
        'commit_sha': request_body.get('commit_sha')
    }))

    # build artifacts. this will clone the git repo and build artifacts.
    build_and_push_artifacts_response = json.loads(call_function('build_and_push_artifacts', json.dumps({
        'git_url': request_body.get('clone_url'),
        'git_commit': request_body.get('commit_sha'),
        'git_branch': request_body.get('git_branch'),
    })))

    # get artifact_urls & artifact_tests from build_and_push_artifacts_response
    artifact_urls = build_and_push_artifacts_response.get('artifact_urls')
    artifact_tests = build_and_push_artifacts_response.get('tests_paths')

    # save artifact URLs in job
    cur.execute('update jobs set artifact_urls = %s where oid = %s', (json.dumps(artifact_urls), job_oid))

    # for each artifact test, create a “test case” object in the database
    for artifact_test in artifact_tests:
        cur.execute('insert into test_cases (job, artifact_test) values (%s, %s)', (job_oid, artifact_test))

    # check if free nodes selection returns a value, if not -> there are no free nodes, so return
    cur.execute('select oid from nodes where current_test_case = -1')
    if cur.fetchall() is None:
        context.logger.info('No more free nodes, quitting.')
        return

    # iterate over the tests of the job
    cur.execute('select oid from test_cases where job = %s', (job_oid, ))
    for test_case in cur.fetchall():

        # get first value (relevant one) of the returned postgresSql tuple
        test_case = test_case[0]

        # get an idle node
        cur.execute(f'select oid from nodes where current_test_case = -1')

        # if there’s no idle node, we’re done
        idle_node = cur.fetchone()

        if idle_node is None:
            context.logger.info('No more idle_nodes, quitting.')
            return

        # get first value (relevant one) of the returned postgresSql tuple
        idle_node = idle_node[0]

        # set the test case running on that node in the db
        cur.execute('update nodes set current_test_case = %s where oid=%s', (test_case, idle_node))

        # run the specific test case on the specific node. since this is the first time this node will
        # run a test, pull is required
        context.logger.info_with('Starting test case', Node=idle_node, Test_case_id=test_case)

        call_function('run_test_case', json.dumps({
            'node': idle_node,
            'pull_mode': 'pull',
            'test_case_id': test_case,
        }))


# get slack username from db according to given github_username
def convert_slack_username(db_cursor, github_username):

    # convert github username to slack username
    db_cursor.execute('select slack_username from users where github_username=%s', (github_username, ))

    # get slack username of given github username
    slack_username = db_cursor.fetchone()

    if slack_username is None:
        raise ValueError('Failed converting git username to slack username')

    # get first value of the postgresSQL tuple answer
    return slack_username[0]


# create job, return id of that job
def create_job(db_cursor):

    # create a db job object with information about this job. set the
    # state to building artifacts
    db_cursor.execute('insert into jobs (state) values (1) returning oid')

    # get OID of inserted job
    job_oid = db_cursor.fetchone()[0]

    return job_oid


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
        'run_test_case': 36547,
        'test_case_complete': 36548
    }

    # if given_host is specified post it instead of
    given_host = os.environ.get('DOCKER_HOST', '172.17.0.1')
    response = requests.post(f'http://{given_host}:{functions_ports[function_name]}',
                             data=function_arguments)

    return response.text
