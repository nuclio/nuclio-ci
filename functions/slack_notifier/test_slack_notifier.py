import sys
sys.path.append("/home/ilayk/work/nuclio-ci")


class TestCase(nuclio_sdk.TestCase):

    def test_slack_notifier(self):

        # keep the situation clean - init_database before
        cur = self._platform.context.user_data.conn.cursor()

        self._platform.context.platform.call_function(36545, nuclio_sdk.Event(body={
            'slack_username': 'ilayk',
            'message': 'Your Nuci test started'
        }))

