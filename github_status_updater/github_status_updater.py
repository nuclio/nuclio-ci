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
    repo_owner_username = os.environ.get('REPO_OWNER_USERNAME')
    repo_owner_token = os.environ.get('REPO_OWNER_OAUTH_TOKEN')

    if not (repo_owner_username and repo_owner_token):
        raise NameError('Local variable REPO_OWNER_USERNAME or REPO_OWNER_OAUTH_TOKEN could not be found')

    session.auth = (repo_owner_username, repo_owner_token)

    # resolve url from request_body, update state of commit to given state
    # with github-api
    session.post('{0}/statuses/{1}'.format(request_body['repo_url'], request_body['commit_sha']),
                 json={'state': request_body['state']})


# calls given function with given arguments
def call_function(function_name, function_arguments=None):
    functions_ports = {'database_init': 36543,
                       'github_status_updater': 36544,
                       'slack_notifier': 36545}

    # if given_host is specified post it instead of
    given_host = os.environ.get('DOCKER_HOST', '172.17.0.1')
    requests.post('http://{0}:{1}'.format(given_host, functions_ports[function_name]),
                  data=function_arguments)
