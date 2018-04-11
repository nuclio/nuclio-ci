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
    session.post(f'{request_body.get("repo_url")}/statuses/{request_body.get("commit_sha")}',
                 json={'state': request_body['state']})


# calls given function with given arguments, returns body of response
def call_function(function_name, function_arguments=None):
    functions_ports = {
        'database_init': 36543,
        'github_status_updater': 36544,
        'slack_notifier': 36545,
        'build_and_push_artifacts': 36546,
        'run_test_case': 36547
    }

    # if given_host is specified post it instead of
    given_host = os.environ.get('DOCKER_HOST', '172.17.0.1')
    response = requests.post(f'http://{given_host}:{functions_ports[function_name]}',
                             data=function_arguments)

    return response.text
