import libs.common.psycopg2_functions
import libs.common.nuclio_helper_functions
from libs import nuclio_sdk

conte = None

def handler(context, event):
    global conte
    conte = context

    request_body = event.body
    test_id = request_body.get('test_case')
    test_result = request_body.get('test_case_result')

    context.logger.debug(test_id)
    context.logger.debug(test_result)
    # cur is the cursor of current connection
    cur = context.user_data.conn.cursor()

    # update test case result
    cur.execute('update test_cases set result=%s where oid=%s', (test_result, test_id))

    # get current running node & current job
    current_node, current_job, job_state = _get_current_job_node_state(cur, test_id)

    # if test failed - release the node!
    if job_state == 'failed':

        context.logger.debug('failed')
        context.platform.call_function('release-node', nuclio_sdk.Event(body={
            'node_id': current_node,
        }))

    # lock job for writes so we don’t clash with another test running on another node, since
    # we are updating the job’s properties
    # test_case.job.lock()

    # if test failed, set the job as failed, update test result, report job result with github & slack & release node
    if test_result == 'failure':
        context.logger.debug('failed2')
        _test_failed(context, cur, current_job, current_node, test_id)

    # if the test succeeded, check if we should run another test on this node
    # or release it into the wild
    else:

        # get the next test without a result and without a node
        next_pending_test_id = get_next_test_id(cur)
        context.logger.debug(next_pending_test_id)

        # if there’s no test, we were the last test to succeed
        if next_pending_test_id is None:
            context.logger.debug('success')
            _job_succeeded(context, cur, current_job, current_node)
        else:
            context.logger.debug('progress')

            _job_in_progress(context, cur, next_pending_test_id, current_node)

            context.logger.debug('calling di')
            context.platform.call_function('database-init', nuclio_sdk.Event(body=
                    {"fixtures": {"users": [{"github_username": "ilaykav", "slack_username": "ilayk"}]}}
                                                                             ))
            context.logger.debug('ending')


def get_next_test_id(cur):
    cur.execute('select oid from test_cases where running_node is null and result is null')
    ret = cur.fetchall()
    conte.logger.debug(ret)
    returned_value = ret[0]

    # if command returned not-null, return first value of returned tuple,
    return returned_value if returned_value is None else returned_value[0]


def report_job_result(context, cur, current_job, result):
    github_username, git_url, commit_sha = _get_jobs_properties_for_reporting(cur, current_job)

    # get slack username
    slack_username = libs.common.nuclio_helper_functions.convert_slack_username(cur, github_username)

    # notify via slack that build is running
    context.platform.call_function('slack-notifier',  nuclio_sdk.Event(body={
        'slack_username': slack_username,
        'message': result
    }))


def report_job_logs(context, cur, current_job, current_test):
    github_username, git_url, commit_sha = _get_jobs_properties_for_reporting(cur, current_job)

    # get slack username
    slack_username = libs.common.nuclio_helper_functions.convert_slack_username(cur, github_username)

    cur.execute('select logs from test_cases where oid = %s', (current_test,))
    logs = cur.fetchone()
    if logs is not None:
        logs = logs[0]

    # notify via slack that build is running
    context.platform.call_function('slack-notifier', nuclio_sdk.Event(body={
        'slack_username': slack_username,
        'message': logs,
        'send_message_in_file': 'True'
    }))


def _get_current_job_node_state(cur, test_id):
    cur.execute('select oid from nodes where current_test_case = %s', (test_id,))
    current_node = cur.fetchall()[0][0]

    cur.execute('select job from test_cases where oid = %s', (test_id,))
    current_job = cur.fetchall()[0][0]

    cur.execute('select state from jobs where oid=%s', (current_job,))
    job_state = cur.fetchall()[0][0]

    return [current_node, current_job, job_state]


def _get_jobs_properties_for_reporting(cur, current_job):
    jobs_properties = []
    needed_parameters = ['github_username', 'github_url', 'commit_sha']
    for parameter in needed_parameters:
        cur.execute(f'select {parameter} from jobs where oid = %s', (current_job,))
        jobs_properties.append(cur.fetchall()[0][0])

    return jobs_properties


def _job_in_progress(context, cur, next_pending_test_id, current_node):

    # set the test case running on that node in the db
    cur.execute('update nodes set current_test_case = %s where oid=%s returning oid',
                (next_pending_test_id, current_node))
    running_node = cur.fetchall()[0]
    cur.execute('update test_cases set running_node = %s where oid=%s', (running_node, next_pending_test_id))

    # run the specific test case on the specific node. since this is the first time this node will
    # run a test, pull is required
    context.logger.info_with('started test case', Node=current_node, Test_case_id=next_pending_test_id)

    context.platform.call_function('run-test-case', nuclio_sdk.Event(body={
        'node': current_node,
        'pull_mode': 'no_pull',
        'test_case_id': next_pending_test_id
    }), wait_for_response=False)


def _job_succeeded(context, cur, current_job, current_node):
    cur.execute('update jobs set state=\'success\' where oid=%s', (current_job,))

    # report job result with slack
    report_job_result(context, cur, current_job, 'success')

    # release the node
    context.platform.call_function('release-node', nuclio_sdk.Event(body={
        'node_id': current_node,
    }))


def _test_failed(context, cur, current_job, current_node, current_test):
    cur.execute('update jobs set state=\'fail\' where oid=%s', (current_job,))

    # report job result with slack
    report_job_result(context, cur, current_job, 'failed')

    # report job's logs with slack
    report_job_logs(context, cur, current_job, current_test)
    context.platform.call_function('release-node', nuclio_sdk.Event(body={
        'node_id': current_node,
    }))


def init_context(context):
    setattr(context.user_data, 'conn', libs.common.psycopg2_functions.get_psycopg2_connection())

