import sys
sys.path.append("/home/ilayk/work/nuclio-ci")
import nuclio_sdk.test
import common.nuclio_helper_functions
import common.psycopg2_functions
import os

class TestCase(nuclio_sdk.TestCase):

    def test_release_node(self):

        cur = self._platform.context.user_data.conn.cursor()
        cur.execute('insert into test_cases values(null) returning oid')
        job_id = cur.fetchall()[0][0]

        cur.execute('insert into nodes values(%s) returning oid', (job_id, ))
        node_id = cur.fetchall()[0][0]

        self._platform.call_function(36550, nuclio_sdk.Event(body={
            'node_id': node_id,
        }), wait_for_response=True)

        cur.execute('select current_test_case from nodes order by oid desc limit 1')
        node_id = cur.fetchall()[0][0]

        self.assertNotEqual(node_id, job_id)
