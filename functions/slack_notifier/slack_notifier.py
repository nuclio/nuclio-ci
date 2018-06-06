import slackclient.client
import requests
import json
import os

SLACK_CLIENT = None


# event should contain: slack_username of target, message for message to be sent
def handler(context, event):
    global SLACK_CLIENT
    request_info = event.body
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

