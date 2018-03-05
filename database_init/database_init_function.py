import json
import pg8000

PGUSERNAME = "postgres"
PGPASSWORD = "pass"
PGHOST = "172.17.0.1"

def handler(context, event):

    # connect to postgres database
    conn = pg8000.connect(host=PGHOST, user=PGUSERNAME, password=PGPASSWORD)

    # get usernames to insert
    git_slack_usernames = json.loads(event.body)
    git_slack_usernames = git_slack_usernames.split()

    # get every even and odd user together, to insert properly in users table
    users = [(git_slack_usernames[i], git_slack_usernames[i+1]) for i in range (0, len(git_slack_usernames), 2)]

    commands = ["create table test_cases (runnind_node oid, logs text, result int, job oid, artifact_test text) with oids",
                "create table nodes (current_test_case oid) with oids",
                "create table jobs (state int) with oids",
                "create table users (github_username text, slack_username text)",
                "insert into users (github_username, slack_username) values {}".format(str(users)[1:-1])]

    # iterate over commands, execute & commit them with the connection
    for command in commands:
        conn.cursor().execute(command)
        conn.commit()

    return context.Response(body='ok')
