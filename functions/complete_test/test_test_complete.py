import sys
sys.path.append("/home/ilayk/work/nuclio-ci")


class TestCase(nuclio_sdk.TestCase):

    def test_test_complete(self):

        # keep the situation clean - init_database before
        cur = self._platform.context.user_data.conn.cursor()

        cur.execute('insert into test_cases(result) values(\'failure\') returning oid')
        test_case_id = cur.fetchall()[0][0]
        print(test_case_id)

        self._platform.call_function(31549, nuclio_sdk.Event(body={
            'test_case': test_case_id,
            'test_case_result': 'failure',
        }))

        # check if got failure on slack
