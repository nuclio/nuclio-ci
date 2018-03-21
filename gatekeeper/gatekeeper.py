import os
import json
import requests


def handler(context, event):

    # Load data from given json
    webhook_request = json.loads(event.body)
    permission_sequence = 'Can one of the admins approve running tests for this PR?'
    launch_word = '@nuci approved'
    whitelist = ['ilaykav']

    if is_event_relevant(webhook_request, launch_word):

        context.logger.info('event relevant')
        if not webhook_request['user']['login'] in whitelist:

            context.logger.info('sender not in whitelist')
            if not whitelister_permitted(get_comments_url(webhook_request), launch_word, whitelist):

                context.logger.info('added comment')
                add_comment_if_doesnt_exist(webhook_request, permission_sequence)

    # got permission -> launch nuci
    # call_function('run_job')
    context.logger.info('start nuci')


# add comment to issue's comments if it's not already there
def add_comment_if_doesnt_exist(webhook_request, permission_sequence):

    # if permission sequence not in comments add one
    if not is_in_comments(webhook_request, permission_sequence):
        session = get_github_session()
        session.post(get_comments_url()[:-5]+get_last_commit_sha(webhook_request), json={'body': permission_sequence})


# return if comment is white-listed
def is_comment_author_white_listed(webhook_request, whitelist):
    return webhook_request['user']['login'] in whitelist


# implement isin_comments() with is_comment_white_listed() to check for presence of whitelister approval
def whitelister_permitted(comments_url, launch_word, whitelist):
    return is_in_comments(comments_url, launch_word, is_comment_author_white_listed, whitelist)

# checks if given str1 contains str2
def contains_ignore_case(str1, str2):
    return str2.lower() in str1.lower()


# returns if it's issue comment & relevant - ignore other comments
def is_event_relevant(webhook_request, launch_word):
    try:

        # If it's comment, return true if the author is whitelisted
        comment = webhook_request['comment']
        return is_comment_author_white_listed(comment) and contains_ignore_case(comment['body'], launch_word)
    except KeyError:

        # is not comment
        return True
    return False


# check for given word in data, considers function(comment) if more preferences necessary
def is_in_comments(comments_url, data_to_find, other_preference_function = None):
    num_page = 1
    session = get_github_session()
    comments = session.get(comments_url, params={'page': num_page})
    comments = json.loads(comments.text)

    # Iterate over comments until given word found, or end of comments
    while comments:
        for comment in comments:
            if contains_ignore_case(comment['body'], data_to_find) and \
               other_preference_function(comment) if other_preference_function else True:
                return True

        num_page += 1
        comments = session.get(comments_url, params={'page': num_page})
        comments = json.loads(comments.text)

    return False


def get_github_session():
    repo_owner_token = os.environ.get('REPO_OWNER_DETAILS')

    if not repo_owner_token:
        raise NameError('Local variable REPO_OWNER_DETAILS')

    session = requests.Session()
    session.auth = ('Nuci314', 'Nucitoken')
    return session


# calls given function with given arguments
def call_function(function_name, function_arguments=None):
    functions_ports = {
        'database_init': 36543,
        'github_status_updater': 36544,
        'slack_notifier': 36545
    }

    # if given_host is specified post it instead of
    given_host = os.environ.get('DOCKER_HOST', '172.17.0.1')
    requests.post('http://{0}:{1}'.format(given_host, functions_ports[function_name]),
                  data=function_arguments)


# get last commit of PR mentioned in the github response
def get_last_commit_sha(request_body):
    session = get_github_session()
    commits = 'commits'
    next_commits = commits
    num_page = 1
    action_type = request_body['action']

    # iterate over commits until reaching end of them (in case of github api
    # sending multiple pages)
    while True:

        # handle cases where jsons are different
        if action_type == 'created':
            next_commits = session.get('{}/commits'.format(
                request_body['issue']['pull_request']['url']),
                params={'page': num_page}
            )
        elif action_type == 'synchronize':
            next_commits = session.get(
                '{}/commits'.format(request_body['pull_request']['url']),
                params={'page': num_page})

        # break when next page is empty
        if not json.loads(next_commits.text):
            break

        commits = json.loads(next_commits.text)
        num_page += 1

    # get last commit's sha
    return commits[-1]['sha']


def get_comments_url(webhook_request):
    action_type = webhook_request['action']
    # handle cases where jsons are different
    if action_type == 'created':
        return webhook_request['issue']['pull_request']['url']

    elif action_type == 'synchronize':
        return webhook_request['pull_request']['url']
