import sys
sys.path.append("/home/ilayk/work/nuclio-ci")

from libs import nuclio_sdk
import libs.common.nuclio_helper_functions


class TestCase(nuclio_sdk.TestCase):

    def test_basic_build_push(self):

        artifacts_supposed_tests = ['pkg/cmdrunner', 'pkg/common', 'pkg/dashboard/functiontemplates',
                                   'pkg/dashboard/test', 'pkg/dockerclient', 'pkg/dockercreds', 'pkg/errors',
                                   'pkg/functionconfig', 'pkg/nuctl/test', 'pkg/platformconfig', 'pkg/processor/build',
                                   'pkg/processor/build/inlineparser', 'pkg/processor/build/runtime/dotnetcore/test',
                                   'pkg/processor/build/runtime/golang/eventhandlerparser',
                                   'pkg/processor/build/runtime/golang/test', 'pkg/processor/build/runtime/java/test',
                                   'pkg/processor/build/runtime/nodejs/test', 'pkg/processor/build/runtime/pypy/test',
                                   'pkg/processor/build/runtime/python', 'pkg/processor/build/runtime/python/test',
                                   'pkg/processor/build/runtime/shell/test', 'pkg/processor/build/test',
                                   'pkg/processor/config',
                                   'pkg/processor/runtime/dotnetcore/test', 'pkg/processor/runtime/golang',
                                   'pkg/processor/runtime/golang/test', 'pkg/processor/runtime/java/test',
                                   'pkg/processor/runtime/nodejs/test', 'pkg/processor/runtime/pypy/test',
                                   'pkg/processor/runtime/python/test', 'pkg/processor/runtime/rpc',
                                   'pkg/processor/runtime/shell/test', 'pkg/processor/trigger/cron',
                                   'pkg/processor/trigger/cron/test', 'pkg/processor/trigger/kafka/test',
                                   'pkg/processor/trigger/nats/test', 'pkg/processor/trigger/rabbitmq',
                                   'pkg/processor/trigger/rabbitmq/test', 'pkg/processor/worker',
                                   'pkg/registry', 'pkg/restful']

        artifacts_supposed_urls = ['nuclio/controller:latest-amd64',
                                   'nuclio/playground:latest-amd64',
                                   'nuclio/dashboard:latest-amd64',
                                   'nuclio/processor-py2.7-alpine:latest-amd64',
                                   'nuclio/processor-py2.7-jessie:latest-amd64',
                                   'nuclio/processor-py3.6-alpine:latest-amd64',
                                   'nuclio/processor-py3.6-jessie:latest-amd64',
                                   'nuclio/handler-builder-golang-onbuild:latest-amd64',
                                   'nuclio/processor-pypy2-5.9-jessie:latest-amd64',
                                   'nuclio/handler-pypy2-5.9-jessie:latest-amd64',
                                   'nuclio/processor-shell-alpine:latest-amd64',
                                   'nuclio/handler-nodejs-alpine:latest-amd64',
                                   'nuclio/handler-builder-dotnetcore-onbuild:latest-amd64',
                                   'nuclio/handler-java:latest-amd64',
                                   'nuclio/handler-builder-java-onbuild:latest-amd64',
                                   'nuclio/user-builder-java-onbuild:latest-amd64']

        supposed_uploaded_images = ["controller","dashboard","handler-builder-dotnetcore-onbuild",
                                    "handler-builder-golang-onbuild","handler-builder-java-onbuild",
                                    "handler-java","handler-nodejs-alpine","handler-pypy2-5.9-jessie",
                                    "playground","processor-py2.7-alpine","processor-py2.7-jessie",
                                    "processor-py3.6-alpine","processor-py3.6-jessie","processor-pypy2-5.9-jessie",
                                    "processor-shell-alpine","tester","user-builder-java-onbuild"]

        build_and_push_artifacts_response = self._platform.call_function(function_indicator=36546,
            event=nuclio_sdk.Event(body={
                'git_url': 'https://github.com/ilaykav/nuclio.git',
                'git_commit': '4db2b5529a26b16ff8018a4c10eeb37e723a570c',
                'git_branch': 'nuclio-ci-tmp-test-branch',
            }), wait_for_response=True)

        artifact_urls = build_and_push_artifacts_response.body.get('artifact_urls')
        artifact_tests = build_and_push_artifacts_response.body.get('tests_paths')

        print(build_and_push_artifacts_response)
        print(str(artifact_urls) + ',  ' + str(artifact_tests))

        for supposed_test in artifacts_supposed_tests:
            if supposed_test not in artifact_tests:
                self.assertIn('Not all artifact-artifact_tests were figured out - missing', supposed_test)

        for supposed_url in artifacts_supposed_urls:
            if supposed_url not in artifact_urls:
                self.assertIn('Not all artifact-urls were figured out - missing', supposed_url)

        up_images = libs.common.nuclio_helper_functions.run_command(
            self._platform.context,
            'curl -X GET  -k http://localhost:5000/v2/_catalog'
        )

        for suppsed_uploaded_image in supposed_uploaded_images:
            if suppsed_uploaded_image  not in up_images:
                self.assertIn('Not all images were pushed to local registry on localhost:5000- missing', supposed_test)
