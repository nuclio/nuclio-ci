import requests
import json
import os


# event contains requset_body, which contains:
#   state - state of commit to be updated
#   commit_sha - sha of commit for updating state
#   repo_url - commit's repository url
def handler(context, event):
    request_body = json.loads(event.body)
    session = requests.Session()

    # get username & password from container's environment vars
    repo_owner_username, repo_owner_token = os.environ.get('REPO_OWNER_USERNAME'),
    os.environ.get('REPO_OWNER_OAUTH_TOKEN')
    if not (repo_owner_username and repo_owner_token):
        raise NameError('Local variable REPO_OWNER_USERNAME or REPO_OWNER_OAUTH_TOKEN could not be found')

    session.auth = (repo_owner_username, repo_owner_token)

    # resolve url from request_body, update state of commit to given state
    # with github-api
    session.post('{0}/statuses/{1}'.format(request_body['repo_url'], request_body['commit_sha']),
                 json={'state': request_body['state']})
