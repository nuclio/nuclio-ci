import os
import json
import parse
import requests


# get a webhook report in event.data, launch nuci if needed & permitted
def handler(context, event):

    # Load data from given json
    webhook_report = json.loads(event.body)
    permission_sequence = 'Can one of the admins approve running tests for this PR?'
    launch_word = '@nuci approved'
    whitelist = ['ilaykav']

    # check if event is not relevant don't do anything
    if not is_event_relevant(webhook_report, launch_word, whitelist):
        return

    # check if pull request author is whitelisted -> start nuci
    # if it's a comment -> it's a relevant comment (because of is_event_relevant()) -> start nuci
    if webhook_report.get('comment') is None and webhook_report['pull_request']['user']['login'] not in whitelist:

        # check if any admin permitted the PR, if so start nuci
        if not admin_permitted(get_comments_url(webhook_report), launch_word, whitelist):

            # add comment only if not added yet asking for admin to whitelist the PR
            add_comment_if_doesnt_exist(webhook_report, permission_sequence)
            return

    # TODO: call_function('run_job')
    context.logger.info('start nuci')


# implement is_in_comments() with is_comment_white_listed() to check for presence of whitelister approval
def admin_permitted(comments_url, launch_word, whitelist):
    return is_in_comments(comments_url,
                          launch_word,
                          lambda comment_preferences: comment_preferences['user']['login'] in whitelist)


# add comment to issue's comments if it's not already there
def add_comment_if_doesnt_exist(webhook_report, permission_sequence):

    # if permission sequence not in comments add one
    if not is_in_comments(get_comments_url(webhook_report), permission_sequence):
        session = get_github_authenticated_session()
        session.post(get_comments_url(webhook_report), json={'body': permission_sequence})


# checks if given str1 contains str2
def contains_ignore_case(str1, str2):
    return str2.lower() in str1.lower()


# returns if it's issue comment & relevant - ignore other comments
def is_event_relevant(webhook_report, launch_word, whitelist):

    # If it's a comment, return true if the author is whitelisted and comment contains launch_word
    comment = webhook_report.get('comment')
    if comment is not None:
        return comment['user']['login'] in whitelist and contains_ignore_case(comment['body'], launch_word)
    return True


# check for given word in any comment body, considers function(comment) if more preferences necessary
def is_in_comments(comments_url, string_to_find, other_preference_function=None):
    num_page = 0
    session = requests.Session()
    comments = json.loads(session.get(comments_url).text)

    # iterate over comments until given word found or end of comments
    while comments:
        for comment in comments:

            # check if comment's body contains string_to_find & if
            # other_preference_function given check if it returns true
            if contains_ignore_case(comment['body'], string_to_find) and \
               other_preference_function(comment) if other_preference_function else True:
                return True

        num_page += 1
        comments = json.loads(session.get(comments_url, params={'page': num_page}).text)
    return False


# returns github authenticated session, using given environmental variable REPO_OWNER_DETAILS
def get_github_authenticated_session():

    # env var REPO_OWNER_DETAILS should be in pattern username:access_token
    repo_owner_details = tuple(parse.parse('{}:{}', os.environ.get('REPO_OWNER_DETAILS')))

    # if REPO_OWNER_DETAILS is None, raise NameError
    if not repo_owner_details:
        raise NameError('Local variable REPO_OWNER_DETAILS does not exist / not in the right format of '
                        'username:access_token')

    session = requests.Session()
    session.auth = repo_owner_details
    return session


# return comments_url of the PR
def get_comments_url(webhook_report):
    action_type = webhook_report['action']
    # handle cases where jsons are different
    if action_type == 'created':
        return webhook_report['issue']['pull_request']['comments_url']

    return webhook_report['pull_request']['comments_url']
