import psycopg2
import psycopg2.sql
import os
import json
import parse
import requests


# gets test_id, test)result
from plainbox.impl import test_resource


def handler(context, event):
    request_body = json.loads(event.body)
    test_id = request_body.get('test_id')
    test_result = request_body.get('test_result')

    # get a connection to the postgresSql database
    conn = connect_to_db()

    # cur is the cursor of current connection
    cur = conn.cursor()

    cur.execute('update test_cases set result=%s where oid=%s', (test_result, test_id))

    if test_result != 'failed':
        return release_noes()

        # lock job for writes so we don’t clash with another test running on another node, since
        # we are updating the job’s properties
    # test_case.job.lock()

    # if the test failed, set the job as failed
    if test_result == 'failed':

        cur.execute('update test_cases set result=%s where oid=%s', (test_result, test_id))


def get_next_test_id(cur):
    cur.execute('select oid from test_cases where runnind_node is null and result is null')
    returned_value = cur.fetchone()

    # if command returned not-null, return first value of returned tuple,
    return returned_value if returned_value is None else returned_value[0]


def report_job_result(cur, github_username, git_url, commit_sha):

    # get slack username
    slack_username = convert_slack_username(cur, github_username)

    # notify via slack that build is running
    call_function('slack_notifier', json.dumps({
        'slack_username': slack_username,
        'message': 'Your Nuci test started'
    }))

    # notify via github that build is running
    call_function('github_status_updater', json.dumps({
        'state': 'pending',
        'repo_url': git_url,
        'commit_sha': commit_sha
    }))


def release_noes(node):
    pass




# returns map with {
# artifact-tests-url: value,
# state: state_value,
# github_url: github_url_value,
# commit_sha: commit_sha_value,
# github_username: github_username_value}
def get_job_properties(cur, test_id):
    cur.execute('select job from test_cases where oid=%s', (test_id, ))
    job_properties = cur.fetchone()

    if job_properties is None:
        return None;

    keys = cur.execute(f'\d test_cases;')
    map = {}

    for key_index, key in enumerate(keys):
        map[key] = job_properties[key_index]

    return job_properties[]


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



# gets current cursor and command, alerts if returned 0 values
def get_cursors_one_result(cur, cmd):
    returned_value = cur.fetchone()

    if returned_value is None:
        return Exception(cmd)

    return returned_value[0]


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
        'run_test_case': 36547
    }

    # if given_host is specified post it instead of
    given_host = os.environ.get('DOCKER_HOST', '172.17.0.1')
    response = requests.post(f'http://{given_host}:{functions_ports[function_name]}',
                             data=function_arguments)

    return response.text


