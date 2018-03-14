import slackclient.client
import requests
import json
import os

SLACK_CLIENT = None


# event should contain: slack_username of target
def handler(context, event):
        global SLACK_CLIENT
        request_info = json.loads(event.body)
        slack_username = request_info['slack_username']

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
            channel='@{0}'.format(slack_username),
            text='Your Nuci test started',
        )

        # check send result, log & raise errors accordingly
        if slackbot_send_result['ok']:
            context.logger.info_with('Message sent successfully', user=slack_username)
        else:

            # raise connection error - the sending process failed
            raise requests.ConnectionError(
                'failed to send message to user {0}, response from slack - {1}'.format(
                    slack_username,
                    slackbot_send_result))
