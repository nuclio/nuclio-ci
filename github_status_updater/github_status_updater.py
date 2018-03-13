import requests
import json


# event contains requset_body, which contains:
#   status - state of commit to be updated
#   event_info - information needed for updating
def handler(context, event):
    request_body = json.loads(event.body)
    session = requests.Session()

    # for updating github's status it is needed to be the repo's owner
    session.auth = ('ilaykav', 'ilaykavtoken')

    # get last commit's sha
    last_commit_sha = get_last_commit_sha(request_body['event_info'])

    # resolve url from request_body, update status of commit to given status
    # with github-api
    url = request_body['event_info']['repository']['statuses_url']
    session.post(url[:-5] + last_commit_sha,
                 data='{\'state\': \'{}\'}'.format(request_body['status']))


# get last commit of PR mentioned in the github response
def get_last_commit_sha(request_body):
    session = requests.Session()
    session.auth = ('Nuci314', 'Nucitoken')
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
