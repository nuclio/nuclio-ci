import psycopg2
import psycopg2.sql
import os
import json
import parse
import requests

# this local function calls a remote function called release node.
# release_node:
# looks for jobs that the node should attach to. if there are none,
# just stays idle. if there is one, start running its tests


def handler(context, event):
    request_body = json.loads(event.body)
    current_node_id = request_body.get('node_id')

    # get a connection to the postgresSql database
    conn = connect_to_db()

    # cur is the cursor of current connection
    cur = conn.cursor()

    # gather test case result
    cur.execute('select current_test_case from nodes where oid=%s', (current_node_id,))
    current_test_case = cur.fetchall()[0]

    # get job
    cur.execute('select job from test_cases where oid=%s', (current_test_case,))
    current_job_id = cur.fetchall()[0]

    # first - check if there is test need to be done in our job's artifact test
    cur.execute('select artifact_test from test_cases where running_node is null and job = %s', (current_job_id,))
    artifact_test = None if cur.fetchall() is None else cur.fetchall()[0]

    # if artifact is none, no other tests required in our job, start new test-case
    if artifact_test is None:
        run_foreign_test_case(cur, current_node_id)

    # found another test need to be done in same job - run_test_case without pull required
    else:
        call_function('run_test_case', json.dumps({'node': current_node_id,
                                                   'pull_required': False,
                                                   'test_case_id': current_test_case }))

    # if not found any job - leave the node idle
    return


def run_foreign_test_case(cur, current_node_id):
    cur.execute('select oid from test_cases where running_node is null')
    new_test_case_id = None if cur.fetchall() is None else cur.fetchall()[0]

    call_function('run_test_case', json.dumps({'node': current_node_id,
                                               'pull_required': True,
                                               'test_case_id': new_test_case_id}))


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


