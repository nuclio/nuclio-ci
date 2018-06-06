import json
import common.psycopg2_functions
import common.nuclio_helper_functions
import nuclio_sdk

# this local function calls a remote function called release node.
# release_node:
# looks for jobs that the node should attach to. if there are none,
# just stays idle. if there is one, start running its tests


def handler(context, event):
    request_body = event.body
    current_node_id = request_body.get('node_id')

    # get a connection to the postgresSql database
    conn = context.user_data.conn.cursor()

    # cur is the cursor of current connection
    cur = conn.cursor()
    current_test_case = _get_artifact_test_and_current_test_case(cur, current_node_id)

    # if artifact is none, no other tests required in our job, start new test-case
    if current_test_case is None:
        _run_foreign_test_case(cur, current_node_id)
    # else, found another test need to be done in same job - run_test_case without pull required
    else:
        context.platform.call_function('run-test-case',  nuclio_sdk.Event(body={'pull_mode': 'no_pull',
                                                   'test_case_id': current_test_case}))


def _get_artifact_test_and_current_test_case(cur, current_node_id):

    # gather test case result
    cur.execute('select current_test_case from nodes where oid=%s', (current_node_id,))
    current_test_case = cur.fetchall()[0][0]

    return current_test_case


def _run_foreign_test_case(cur, current_node):
    cur.execute('select oid from test_cases where running_node is null')
    new_test_case_id = cur.fetchall()

    # leave idle
    if new_test_case_id is None:
        cur.execute('update nodes set current_test_case = NULL where oid=%s', (current_node, ))
    else:
        new_test_case_id = new_test_case_id[0][0]

    context.platform.call_function('run-test-case',  nuclio_sdk.Event(body={'pull_mode': 'pull',
                                               'test_case_id': new_test_case_id}))


def init_context(context):
    setattr(context.user_data, 'conn', common.psycopg2_functions.get_psycopg2_connection())

