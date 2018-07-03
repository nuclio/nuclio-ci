import sys
sys.path.append("/home/ilayk/work/nuclio-ci")
import libs.common.psycopg2_functions


class TestCase(nuclio_sdk.TestCase):

    def test_run_job(self):

        # keep the situation clean - init_database before
        cur = self._platform.context.user_data.conn.cursor()

        # check if jobs are updated
        cur.execute(
            'insert into nodes values(NULL)')  # , (json.dumps(artifact_urls), job_oid))

        self._platform.context.platform.call_function(36548, nuclio_sdk.Event(body={
            "github_username": 'ilaykav',
            "git_url": 'https://github.com/ilaykav/nuclio',
            "commit_sha": '4db2b5529a26b16ff8018a4c10eeb37e723a570c',
            "git_branch": 'nuclio-ci-tmp-test-branch',
            "clone_url": 'https://github.com/ilaykav/nuclio.git'
        }))

        # We just inserted new node - this node should not be None!
        cur.execute('select current_test_case from nodes order by oid desc limit 1')
        current_test_case = cur.fetchall()[0][0]

        self.assertEqual(current_test_case, None)

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
        setattr(context.user_data, 'conn', libs.common.psycopg2_functions.get_psycopg2_connection())


