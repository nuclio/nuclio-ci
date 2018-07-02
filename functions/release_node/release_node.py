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

    context.logger.debug('current node id : ' + str(current_node_id))
    # get a cursor of connection to the postgresSql database
    cur = context.user_data.conn.cursor()

    # available test case in job
    current_test_case = _get_tests_current_test_case(cur, current_node_id)
    context.logger.debug('current test case: ' + str(current_test_case))

    # if artifact is none, no other tests required in our job, start new test-case
    if current_test_case is None:
        _run_foreign_test_case(context, cur, current_node_id)
    # else, found another test need to be done in same job - run_test_case without pull required
    else:
        context.platform.call_function('run-test-case',  nuclio_sdk.Event(body={'pull_mode': 'no_pull',
                                                   'test_case_id': current_test_case}))


def _get_tests_current_test_case(cur, current_node_id):

    # gather test case result
    cur.execute('select current_test_case from nodes where oid=%s', (current_node_id,))
    current_test_case = cur.fetchall()[0][0]

    # gather test case result
    cur.execute('select job from test_cases where oid=%s', (current_test_case,))
    current_job = cur.fetchall()[0][0]

    if current_job is not None:
        cur.execute('select artifact_urls from jobs where oid=%s', (current_job, ))
        artifact_url = cur.fetchall()[0][0]

        return artifact_url

    return None


def _run_foreign_test_case(context, cur, current_node):
    cur.execute('select oid from jobs where state=\'pending\'')
    new_job_id = cur.fetchall()

    # leave idle
    if new_job_id is None:
        context.logger.debug('didnt found job which needs node')
        cur.execute('update nodes set current_test_case = NULL where oid=%s', (current_node,))
    else:
        new_job_id = new_job_id[0]

    context.logger.debug('found job which needs node')
    cur.execute('select oid from test_cases where running_node is null and job = %s', (new_job_id,))
    new_test_case_oid = cur.fetchall()

    if new_test_case_oid is not None and len(new_test_case_oid) > 0:
        new_test_case_oid = new_test_case_oid[0]
    else:
        context.logger.debug('didnt found job which needs node')
        cur.execute('update nodes set current_test_case = NULL where oid=%s', (current_node,))

    context.logger.debug('new job id : ' + str(new_job_id ))
    context.platform.call_function('run-test-case',  nuclio_sdk.Event(body={'pull_mode': 'pull',
                                                                            'test_case_id': new_test_case_oid }))


def init_context(context):
    setattr(context.user_data, 'conn', common.psycopg2_functions.get_psycopg2_connection())

