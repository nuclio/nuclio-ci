import requests
import json


# requires host, port and send_data
# values which can be specified are send_as_json (default False), auth_username & auth_password (default - not given)
def http_post(host, port, send_data, send_as_json=False, auth_username=None, auth_password=None):
    session = requests.Session()

    # authenticate session if needed
    if (auth_username and auth_password):
        session.auth = (auth_username, auth_password)

    # post request to given host & port. Send as json if specified
    response = requests.post('{0}:{1}'.format(host, port), data=(json.dumps(send_data) if send_as_json else send_data))
    return response
