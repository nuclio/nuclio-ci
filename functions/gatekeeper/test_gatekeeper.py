import sys
sys.path.append("/home/ilayk/work/nuclio-ci")

from libs import nuclio_sdk


class TestCase(nuclio_sdk.TestCase):

    def test_gatekeeper(self):

        # Needs to launch nuclio-ci
        with open("gatekeeper_permitted_packet") as f:
            webhook_packet = f.read()
            gatekeeper_response = self._platform.context.platform.call_function(31548,
                                                                                nuclio_sdk.Event(body={'s':str(webhook_packet)}),
                                                                                wait_for_response=True)
            self.assertNotEqual(gatekeeper_response, 'Nuci started')

        # Doesn't need to launch nuclio-ci
        with open("gatekeeper_not_permitted_packet") as f:
            webhook_packet = f.read()
            gatekeeper_response = self._platform.call_function(31548, nuclio_sdk.Event(body={'s':str(webhook_packet)}),
                                                               wait_for_response=True)
            self.assertNotEqual(gatekeeper_response, 'Nuci not permitted to start')
