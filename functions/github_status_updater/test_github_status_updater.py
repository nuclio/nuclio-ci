import sys
sys.path.append("/home/ilayk/work/nuclio-ci")

import nuclio_sdk.test
import common.nuclio_helper_functions
import requests
import os


class TestCase(nuclio_sdk.TestCase):

    def test_github_status(self):

        # notify via github that build is running
        self._platform.context.platform.call_function(36544, nuclio_sdk.Event(body={
            'state': 'pending',
            'repo_url': 'https://github.com/ilaykav/nuclioTestService',
            'commit_sha': '84ea04abcd2111e4e8705d7f98b0dc2c72f53a13'
        }))

def get_commit_state(repo_url, commit_sha):
    session = requests.Session()

    # get username & password from container's environment vars
    repo_owner_username = os.environ.get('REPO_OWNER_USERNAME')
    repo_owner_token = os.environ.get('REPO_OWNER_OAUTH_TOKEN')

    if not (repo_owner_username and repo_owner_token):
        raise NameError('Local variable REPO_OWNER_USERNAME or REPO_OWNER_OAUTH_TOKEN could not be found')

    session.auth = (repo_owner_username, repo_owner_token)

    # resolve url from request_body, update state of commit to given state
    # with github-api
    status_response = session.get(f'{repo_url}/statuses/{commit_sha}')
    return status_response.get('state')
