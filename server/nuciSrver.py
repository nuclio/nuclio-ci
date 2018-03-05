from slackclient import SlackClient
import pg8000
import socket
import json
import requests


INIT_DB_PORT = 12355
ALREADY_INIT_DATABASE = False
USERS = ["ilaykav", "ilayk"]
PGUSERNAME = "postgresusername"
PGPASSWORD = "passpassword"
PGHOST = "172.17.0.1"
PERMISSION_SEQUENCE = "Can one of the admins approve running tests for this PR?"
LAUNCH_WORD = "@nuci approved"
WHITELIST = ['ilaykav']


# add comment to issue's comments if it's not already there
def add_comment_if_doesnt_exist(data):

    # if permission sequence not in comments add one
    if not is_in_comments(data, PERMISSION_SEQUENCE):
        session = requests.Session()
        session.auth = ('Nuci314', 'Nucitoken')
        session.post(data["issue"]["comments_url"], data="{\"body\" : \"{}\"}".format(PERMISSION_SEQUENCE))


# return if comment is white-listed
def is_comment_author_white_listed(data):
    return data["user"]["login"] in WHITELIST


# implement isin_comments() with is_comment_white_listed() to check for presence of whitelister approval
def whitelister_permitted(data):
    return is_in_comments(data, LAUNCH_WORD, is_comment_author_white_listed)

# checks if given str1 contains str2
def contains_ignore_case(str1, str2):
    return str2.lower() in str1.lower()

# returns if it's issue comment & relevant - ignore other comments
def is_event_relevant(data):
    try:

        # If it's comment, return true if the author is whitelisted
        comment = data["comment"]
        return (is_comment_author_white_listed(comment) and contains_ignore_case(comment["body"], LAUNCH_WORD))
    except:

        # is not comment
        return True

    return False

#check for given word in data, considers function(comment) if more preferences necessary
def is_in_comments(data, data_to_find, other_preference_function = None):
    numPage=1
    s = requests.Session()
    s.auth = ('Nuci314', 'Nucitoken')
    comments = s.get(data["issue"]["comments_url"], params={"page":numPage})
    comments = json.loads(comments.text)

    # Iterate over comments until given word found, or end of comments
    while comments:
        for comment in comments:
            if contains_ignore_case(comment["body"], data_to_find) and (other_preference_function(comment) if other_preference_function else True):
                return True

        numPage+=1
        comments = s.get(data["issue"]["comments_url"], params={"page":numPage})
        comments = json.loads(comments.text)

    return False


# check if user is in whitelist
def action_allowed_for_user(data):
    return data["sender"]["login"] in WHITELIST

# Check if sender has permission to launch nuci, return bool presents 'has permission'
def nuci_launch_needed_and_permitted(data):

    if is_event_relevant(data):

        if action_allowed_for_user(data):
            return True

        elif whitelister_permitted(data):
            return True

        # if event is relevant & not permitted (didn't return true add comment if
        # not added yet
        add_comment_if_doesnt_exist(data)

    return False

def db_init():

    # check for past initializations
    if not ALREADY_INIT_DATABASE:

        # act according to functions's response
        if invoke_db_init().text == 'ok':
            ALREADY_INIT_DATABASE = True
            return True
        else:
            context.logger.info("something went wrong with the database initializaion")
            return False
    return True

def invoke_db_init_function():
    response = requests.post("http://172.17.0.1:{}".format(INIT_DB_PORT), data=json.dumps("ilaykav ilayk bobgithub bobslack"))
    return response

def handler(context, event):
    global ALREADY_INIT_DATABASE

    # invoke database initialization if needed, break if init failed
    if not db_init():
        return

    # Load data from given json
    data = json.loads(event.body)

    session = requests.Session()
    session.post(data["issue"]["comments_url"], data="{\"body\" : \"{}\"}".format(PERMISSION_SEQUENCE))

    # Check if has permission
    should_launch = nuci_launch_needed_and_permitted(data)

    # if got permission launch nuci
    if should_launch:
        startNuci(context, data["sender"]["login"], data, data["clone_url"])


def get_slack_id(slack_client, username):
    members = slack_client.api_call("users.list")["members"]

    for member in members:
        if member["name"].lower() == username.lower():
            return member["id"]

    return ""


def get_last_commit_sha(data):
    session = requests.Session()
    session.auth = ('Nuci314', 'Nucitoken')

    commits = "commits"
    next_commits = commits
    num_page = 1

    # Iterate over commits until reaching end of them (in case of github api sending multiple pages)
    while 1:

        # handle cases where jsons are different
        if data["action"] == "created":
            next_commits = session.get("{}/commits".format(data["issue"]["pull_request"]["url"]), params={"page":num_page})
        elif data["action"] == "synchronize":
            next_commits = session.get("{}/commits".format(data["pull_request"]["url"]), params={"page":num_page})

        # break when next page is empty
        if not json.loads(next_commits.text):
            break

        commits = json.loads(next_commits.text)
        num_page += 1

    # get last commit's sha
    return commits[-1]["sha"]


def update_github_status(context, status, data):
    session = requests.Session()

    # for updating github's status it is needed to be the repo's owner
    session.auth = ('ilaykav', 'ilaykavtoken')

    # get last commit's sha
    last_commit_sha = get_last_commit_sha(data)

    url = data["repository"]["statuses_url"]
    session.post(url[:-5]+last_commit_sha, data='{"state": "{}"}'.format(status))


def get_slackuser_name(conn, github_username, context):
    curser = conn.curser()
    curser.execute("SELECT slack_username FROM users where git_username ='{}'".format(github_username))
    response = cursor.fetchall()

    # check if github_username exists in database
    if response:
        return response[0][0]
    else:
        context.logger.info("username: {} is not registered in the db. message not sent".foramt(username))
        return ""

def notify_slack(context, slack_username, conn, slack_client):

        # get user's slack_id using slack username
        user_slack_id = get_slack_id(slack_client, slack_username)

        # check if id found in slackbot's environment
        if not user_slack_id:
            context.logger.info("failed to recieve user's id - username " + slack_username)
            return

        # send a "Nuci startred" message to the user
        slackbot_send_result = slack_client.api_call("chat.postMessage", channel=user_slack_id, text="Your Nuci test started", as_user=True)

        # check send result, log accordingly
        if slackbot_send_result["ok"]:
            context.logger.info("message sent successfully")
        else:
            context.logger.info("failed to send message to user {}, id {}".format(slack_username, user_slack_id))



def connect_postgres(pguser, pgpassword, pghost):
    conn = pg8000.connect(host=pghost, user=pguser, password=pgpassword)
    return conn


def clone_repo_url():
    pass

# start Nuci
def startNuci(context, github_username, data, clone_repo_url):
    context.logger.info("Nuci started")

    # init slack and postgres clients
    slack_client = SlackClient('slacktoken')
    conn = connect_postgres(PGUSERNAME, PGPASSWORD, PGHOST)

    # insert new job into jobs table in our postgres container
    conn.cursor().execute("insert into jobs (state) values (building_cr)")
    conn.commit()

    # get slackusername
    slack_username = get_slackuser_name(conn, github_username, context)
    if not slack_username:
        context.logger.log(" didn't found {}'s slack username".format(github_username))

    # notify with slack that build started
    notify_slack(context, slack_username, conn, slack_client)

    # update last commit's status on github
    update_github_status(context, "pending", data)

    # clone_repo_url


