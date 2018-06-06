import common.psycopg2_functions
import os
import json
import parse
import requests
import nuclio_sdk

PERMISSION_SEQUENCE = 'Can one of the admins approve running tests for this PR?'
LAUNCH_WORD = '@nuci approved'


# get a webhook report in event.body, launch nuci if needed & permitted
def handler(context, event):

    # Load data from given json, init relevant variables
    webhook_report = event.body
    session = create_github_authenticated_session()
    pr = Pr(webhook_report, session)

    # check if event is not relevant don't do anything
    if not event_warrants_starting_integration_test(webhook_report):
        return

    # check if action allowed to run_integration_tests, start nuci if true
    if not check_action_allowed(pr.author, 'run_integration_tests'):

        # check if anyone permitted the PR, start nuci if true
        if not check_pr_whitelisted(pr, LAUNCH_WORD):

            # add comment only if not added yet asking for whitelister to whitelist the PR
            pr.add_comment(PERMISSION_SEQUENCE, exclusive=True)
            return

    # event body should contain: git_url, github_username, commit_sha, git_branch
    context.logger.info("Nuci started")

    context.platform.call_function("run-job", nuclio_sdk.Event(body={
        "github_username": webhook_report["pull_request"]["user"]["login"],
        "git_url": webhook_report["pull_request"]["html_url"],
        "commit_sha": webhook_report["pull_request"]["head"]["sha"],
        "git_branch": webhook_report["pull_request"]["head"]["ref"],
        "clone_url": webhook_report["pull_request"]["head"]["repo"]["git_url"]
    }))


# check if anyone from whitelist allowed run integration tests
def check_pr_whitelisted(pr, launch_word):
    comments = pr.get_comments(launch_word)

    # if comments found with user that allowed to whitelist prs, return true
    for comment in comments:
        if check_action_allowed(comment['user']['login'], 'whitelist_prs'):
            return True

    return False


# return if username allowed, according to given action & username
def check_action_allowed(username, action):
    actions_by_user = {
        'ilaykav': ['run_integration_tests', 'whitelist_prs']
    }

    # return return true if action in user's optional actions
    return action in actions_by_user.get(username, [])


# checks if given str1 contains str2
def contains_ignore_case(str1, str2):
    return str2.lower() in str1.lower()


# returns if the webhook event is relevant
def event_warrants_starting_integration_test(webhook_report):
    return webhook_report['action'] in ['opened', 'reopened', 'synchronize']


# returns github authenticated session, using given environmental variable REPO_OWNER_DETAILS
def create_github_authenticated_session():

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
    def __init__(self, webhook, session):
        self._webhook = webhook
        self._session = session

    # adds a comment with the given body. if exclusive is true, will first call
    # get_comments to verify that it doesn't already exist
    def add_comment(self, body, exclusive=False):
        if exclusive:
            if len(self.get_comments(body)) == 0:
                self._session.post(self._get_comments_url(), json={'body': body})
            return
        self._session.post(self._get_comments_url(), json={'body': body})

    # looks into the comments of the PR and returns the comments matching the body
    def get_comments(self, body=None):
        num_page = 1
        comments = json.loads(self._session.get(self._get_comments_url()).text)
        return_comments = []

        # iterate over comments until given word found or end of comments
        while len(comments) != 0:
            for comment in comments:

                # check if comment's body contains string_to_find & if
                if body is None or contains_ignore_case(comment['body'], body):
                    return_comments.append(comment)

            num_page += 1
            comments = json.loads(self._session.get(self._get_comments_url(), params={'page': num_page}).text)

        return return_comments

    # resolve pr author from pr._webhook
    @property
    def author(self):
        return self._webhook['pull_request']['user']['login']

    # return comments_url of the PR
    def _get_comments_url(self):

        action_type = self._webhook['action']
        # handle cases where jsons are different
        if action_type == 'created':
            print(self._webhook['issue']['pull_request']['comments_url'])
            return self._webhook['issue']['pull_request']['comments_url']

        print(self._webhook['issue']['pull_request']['comments_url'])
        return self._webhook['pull_request']['comments_url']




def init_context(context):
    setattr(context.user_data, 'conn', common.psycopg2_functions.get_psycopg2_connection())

