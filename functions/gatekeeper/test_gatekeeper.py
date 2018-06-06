import nuclio_sdk.test
import common.nuclio_helper_functions


class TestCase(common.test.TestCase):

    def test_gatekeeper(self):

        # Needs to launch nuclio-ci
        with open("gatekeeper_permitted_packet") as f:
            webhook_packet = f.readlines()
            gatekeeper_response = self.__platform.context.platform.call_function("run-job", nuclio_sdk.Event(body={webhook_packet}))
            if gatekeeper_response != 'Nuci started':
                self.assertln('Nuci was supposed to launched')

        # Doesn't need to launch nuclio-ci
        with open("gatekeeper_not_permitted_packet") as f:
            webhook_packet = f.readlines()
            gatekeeper_response = self.__platform.context.platform.call_function("run-job", nuclio_sdk.Event(
                body={webhook_packet}))
            if gatekeeper_response != 'Nuci not permitted to start':
                self.assertln('Nuci was not supposed to launched')
