import os
import json
import parse
import requests


# get a webhook report in event.body, launch nuci if needed & permitted
def handler(context, event):

    # Load data from given json, init relevant variables
    webhook_report = json.loads(event.body)
    permission_sequence = 'Can one of the admins approve running tests for this PR?'
    launch_word = '@nuci approved'
    session = invoke_github_authenticated_session()
    pr = Pr(webhook_report)

    # check if event is not relevant don't do anything
    if not event_warrants_starting_integration_test(webhook_report):
        return

    # check if action allowed to run_integration_tests, start nuci if true
    if not check_action_allowed(pr.author, 'run_integration_tests'):

        # check if anyone permitted the PR, start nuci if true
        if not check_pr_whitelisted(pr, session, launch_word):

            # add comment only if not added yet asking for whitelister to whitelist the PR
            pr.add_comment(permission_sequence, session, exclusive=True)
            return

    # TODO: call_function('run_job')
    context.logger.info('start nuci')


# check if anyone from whitelist allowed run integration tests
def check_pr_whitelisted(pr, session, launch_word):
    comments = pr.get_comments(session, launch_word)

    # if comments found with user that allowed to whitelist prs, return true
    if len(comments) != 0:
        for comment in comments:
            if check_action_allowed(comment['user']['login'], 'whitelist_prs'):
                return True

    return False


# return if username allowed, according to given action & username
def check_action_allowed(username, action):
    run_integration_whitelist = ['ilaykav']
    whitelist_prs = ['ilaykav']

    # return right check-result according to given action & username
    return {
        'run_integration_tests': username in run_integration_whitelist,
        'whitelist_prs': username in whitelist_prs
    }[action]


# checks if given str1 contains str2
def contains_ignore_case(str1, str2):
    return str2.lower() in str1.lower()


# returns if the webhook event is relevant
def event_warrants_starting_integration_test(webhook_report):
    if webhook_report['action'] in ['opened', 'reopened', 'synchronize']:
        return True
    return False


# returns github authenticated session, using given environmental variable REPO_OWNER_DETAILS
def invoke_github_authenticated_session():

    # env var REPO_OWNER_DETAILS should be in pattern username:access_token
    repo_owner_details = parse.parse('{}:{}', os.environ.get('REPO_OWNER_DETAILS'))

    # if REPO_OWNER_DETAILS is None, raise NameError
    if repo_owner_details is None:
        raise NameError('Local variable REPO_OWNER_DETAILS does not exist / not in the right format of '
                        'username:access_token')

    session = requests.Session()
    session.auth = tuple(repo_owner_details)
    return session


# pr object gives pr-related information and actions based on given webhook
class Pr(object):
    def __init__(self, webhook):
        self._webhook = webhook

    # adds a comment with the given body. if exclusive is true, will first call
    # get_comments to verify that it doesn't already exist
    def add_comment(self, body, session, exclusive=False):
        if exclusive:
            if len(self.get_comments(session, body)) == 0:
                session.post(self.get_comments_url(), json={'body': body})
            return
        session.post(self.get_comments_url(), json={'body': body})

    # looks into the comments of the PR and returns the comments matching the body
    def get_comments(self, session, body=None):
        num_page = 1
        comments = json.loads(session.get(self.get_comments_url()).text)
        return_comments = []

        # iterate over comments until given word found or end of comments
        while len(comments) != 0:
            for comment in comments:

                # check if comment's body contains string_to_find & if
                if body is None or contains_ignore_case(comment['body'], body):
                    return_comments.append(comment)

            num_page += 1
            comments = json.loads(session.get(self.get_comments_url(), params={'page': num_page}).text)

        return return_comments

    # return comments_url of the PR
    def get_comments_url(self):
        action_type = self._webhook['action']
        # handle cases where jsons are different
        if action_type == 'created':
            return self._webhook['issue']['pull_request']['comments_url']

        return self._webhook['pull_request']['comments_url']

    # resolve pr author from pr._webhook
    @property
    def author(self):
        return self._webhook['pull_request']['user']['login']
