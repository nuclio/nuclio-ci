import common.psycopg2_functions
import common.nuclio_helper_functions
import json
import nuclio_sdk


# event body should contain: git_url, github_username, commit_sha, git_branch, clone_url, is_testing
def handler(context, event):
    request_body = event.body

    context.logger.debug(request_body)

    # cur is the cursor of current connection
    cur = context.user_data.conn.cursor()

    # insert job and save its OID
    job_oid = create_job(cur,
                         request_body.get("github_username"),
                         request_body.get("git_url"),
                         request_body.get("commit_sha")
                         )

    # get slack username
    slack_username = common.nuclio_helper_functions.convert_slack_username(cur, request_body.get("github_username"))

    # notify via slack that build is running
    context.platform.call_function('slack-notifier', nuclio_sdk.Event(body={
        'slack_username': slack_username,
        'message': 'Your Nuci test started'
    }))

    # notify via github that build is running
    context.platform.call_function('github-status-updater',  nuclio_sdk.Event(body={
        'state': 'pending',
        'repo_url': request_body.get('git_url'),
        'commit_sha': request_body.get('commit_sha')
    }))

    # build artifacts. this will clone the git repo and build artifacts.
    build_and_push_artifacts_response = context.platform.call_function(
        'build-push-artifacts',  nuclio_sdk.Event(body={
            'git_url': request_body.get('clone_url'),
            'git_commit': request_body.get('commit_sha'),
            'git_branch': request_body.get('git_branch'),
        }
    ))

    context.logger.debug(build_and_push_artifacts_response)

    # get artifact_urls & artifact_tests from build_and_push_artifacts_response
    artifact_urls = build_and_push_artifacts_response.body.get('artifact_urls')
    artifact_tests = build_and_push_artifacts_response.body.get('tests_paths')

    # save artifact URLs in job
    cur.execute('update jobs set artifact_urls = %s where oid = %s', (json.dumps(artifact_urls), job_oid))

    # for each artifact test, create a “test case” object in the database
    for artifact_test in artifact_tests:
        cur.execute('insert into test_cases (job, artifact_test) values (%s, %s)', (job_oid, artifact_test))

    # check if free nodes selection returns a value, if not -> there are no free nodes, so return
    cur.execute('select oid from nodes where current_test_case is NULL')
    if cur.fetchall() is None:
        context.logger.info('No more free nodes, quitting.')
        return

    # iterate over the tests of the job
    cur.execute('select oid from test_cases where job = %s', (job_oid, ))
    for test_case in cur.fetchall():

        # get first value (relevant one) of the returned postgresSql tuple
        test_case = test_case[0]

        # get an idle node
        cur.execute(f'select oid from nodes where current_test_case is NULL')

        # if there’s no idle node, we’re done
        idle_node = cur.fetchone()

        if idle_node is None:
            context.logger.info('No more idle_nodes, quitting.')
            return

        # get first value (relevant one) of the returned postgresSql tuple
        idle_node = idle_node[0]

        # set the test case running on that node in the db
        cur.execute('update nodes set current_test_case = %s where oid=%s returning oid', (test_case, idle_node))

        running_node = cur.fetchall()[0]
        cur.execute('update test_cases set running_node = %s where oid=%s', (running_node, test_case))

        context.logger.info(f'update test_cases set running_node = {running_node} where oid={test_case}')

        # run the specific test case on the specific node. since this is the first time this node will
        # run a test, pull is required
        context.logger.info_with('Starting test case', Node=idle_node, Test_case_id=test_case)

        context.platform.call_function('run-test-case',  nuclio_sdk.Event(body={
            'node': idle_node,
            'pull_mode': 'pull',
            'test_case_id': test_case,
        }))


# create job, return id of that job
def create_job(db_cursor, github_username, github_url, commit_sha):

    # create a db job object with information about this job. set the
    # state to building artifacts
    db_cursor.execute(f'insert into jobs (state, github_username, github_url, commit_sha) values '
                      f'(\'pending\', %s, %s, %s) returning oid', (github_username, github_url, commit_sha))

    # get OID of inserted job
    job_oid = db_cursor.fetchone()[0]

    return job_oid


def init_context(context):
    setattr(context.user_data, 'conn', common.psycopg2_functions.get_psycopg2_connection())


