import sys
sys.path.append("/home/ilayk/work/nuclio-ci")


class TestCase(nuclio_sdk.TestCase):

    def test_run_job(self):

        # keep the situation clean - init_database before
        cur = self._platform.context.user_data.conn.cursor()

        # check if jobs are updated
        cur.execute('insert into nodes values(NULL)')

        self._platform.context.platform.call_function(31548, nuclio_sdk.Event(body={
            "github_username": 'ilaykav',
            "git_url": 'https://github.com/ilaykav/nuclio',
            "commit_sha": '4db2b5529a26b16ff8018a4c10eeb37e723a570c',
            "git_branch": 'nuclio-ci-tmp-test-branch',
            "clone_url": 'https://github.com/ilaykav/nuclio.git'
        }), wait_for_response=True)

        # We just inserted new node - this node should not be None!
        cur.execute('select logs from test_cases order by oid desc limit 1')
        current_test_logs = cur.fetchall()[0][0]

        self.assertNotEqual(None, current_test_logs)

