# Copyright 2018 The Nuclio Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import slackclient.client
import requests
import json
import os

SLACK_CLIENT = None


# event should contain: slack_username of target, message for message to be sent
def handler(context, event):
    global SLACK_CLIENT
    request_info = json.loads(event.body)
    slack_username = request_info.get('slack_username')
    message_to_send = request_info.get('message')

    if message_to_send is None:
        raise NameError('Variable \'message\' could not be found in triggering package')

    # init slack_client only if not initialized yet
    if SLACK_CLIENT is None:

        # get slack token from env variable
        slack_token = os.environ.get('NUCLIO_CI_SLACK_TOKEN')

        # raise error if local variable not set
        if slack_token is None:
            raise NameError('Local variable NUCLIO_CI_SLACK_TOKEN could not be found')

        # init slack_client with given slack_token
        SLACK_CLIENT = slackclient.SlackClient(slack_token)

    # send a 'Nuci startred' message to the user
    slackbot_send_result = SLACK_CLIENT.api_call(
        'chat.postMessage',
        channel=f'@{slack_username}',
        text=message_to_send,
    )

    # check send result, log & raise errors accordingly
    if slackbot_send_result['ok']:
        context.logger.info_with('Message sent successfully', user=slack_username)
    else:

        # raise connection error - the sending process failed
        raise requests.ConnectionError(
            f'failed to send message to user {slack_username}, response from slack - {slackbot_send_result}')


# calls given function with given arguments, returns body of response
def call_function(function_name, function_arguments=None):
    functions_ports = {
        'database_init': 36543,
        'github_status_updater': 36544,
        'slack_notifier': 36545,
        'build_and_push_artifacts': 36546,
        'run_test_case': 36547
    }

    # if given_host is specified post it instead of
    given_host = os.environ.get('DOCKER_HOST', '172.17.0.1')
    response = requests.post(f'http://{given_host}:{functions_ports[function_name]}', data=function_arguments)

    return response.text
