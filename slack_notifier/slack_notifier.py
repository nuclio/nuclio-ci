from slackclient import SlackClient
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
        if not SLACK_CLIENT:

            # get slack token from env variable
            slack_token = os.environ.get('NUCLIO_CI_SLACK_TOKEN')

            # raise error if local variable not set
            if not slack_token:
                raise NameError('Local variable NUCLIO_CI_SLACK_TOKEN could not be found')

            # init slack_client with given slack_token
            SLACK_CLIENT = SlackClient(slack_token)

        # get user's slack_id using slack username
        user_slack_id = get_slack_id(SLACK_CLIENT, slack_username)

        # check if id found in slackbot's environment
        if not user_slack_id:
            context.logger.info(
                'ValueError - failed to recieve user\'s id based on given username {0}'.format(slack_username))
            raise ValueError('failed to recieve user\'s id based on given username {1}'.format(slack_username))

        # send a 'Nuci startred' message to the user
        slackbot_send_result = SLACK_CLIENT.api_call(
            'chat.postMessage',
            channel=user_slack_id,
            text='Your Nuci test started',
            as_user=True
        )

        # check send result, log accordingly
        if slackbot_send_result['ok']:
            context.logger.info('message sent successfully')
        else:
            context.logger.info(
                'ConnectionError - failed to send message to user {0}, id {1}, response - {2}'.format(
                    slack_username,
                    user_slack_id,
                    slackbot_send_result
                ))
            raise requests.ConnectionError(
                'failed to send message to user {0}, id {1}'.format(slack_username, user_slack_id))


def get_slack_id(slack_client, username):
    members = slack_client.api_call('users.list')['members']

    for member in members:
        if member['name'].lower() == username.lower():
            return member['id']

    return ''
