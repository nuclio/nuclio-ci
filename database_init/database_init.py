import psycopg2
import os
import json
import parse


# init database, gets github-slack usernames in event.body in format of githubname1_slackname1_githubnameN_slacknameN
def handler(context, event):

    # get postgres connection information from container's environment vars
    postgres_info = parse_info(os.environ.get('PGINFO'))

    # raise NameError if env var not found, or found in wrong format
    if postgres_info is None:
        raise ValueError('Local variable PGINFO in proper format (user:password@host:port or user:password@host)'
                         ' could not be found')

    postgres_user, postgres_password, postgres_host, postgres_port = postgres_info

    # connect to postgres database,
    conn = psycopg2.connect(host=postgres_host, user=postgres_user, password=postgres_password, port=postgres_port)

    # get usernames from request to insert in USERS table
    github_slack_usernames = json.loads(event.body)['users'].split('_')

    # get every even and odd user together, to insert properly in users table
    users = [(github_slack_usernames[i], github_slack_usernames[i + 1])
             for i in range(0, len(github_slack_usernames), 2)]

    # proper commands to initialize database
    commands = ['create table test_cases (runnind_node oid, logs text, result int, job oid,'
                ' artifact_test text) with oids',
                'create table nodes (current_test_case oid) with oids',
                'create table jobs (state int) with oids',
                'create table users (github_username text, slack_username text) with oids',
                'insert into users (github_username, slack_username) values {0}'.format(str(users)[1:-1])]

    # cur is the cursor of current connection
    cur = conn.cursor()

    # iterate over commands, execute them with the cursor
    for command in commands:
        cur.execute(command)

    # commit changes
    conn.commit()


# gets string to process, return None if format is wrong, list of info if format is well writen -
# return-list : username, password, host, port
def parse_info(formatted_string):
    if formatted_string is not None:

        # check if default formatted string given
        if parse.parse('{}:{}@{}:{}', formatted_string) is not None:
            return list(parse.parse('{}:{}@{}:{}', formatted_string))

        # if not, try get same format without the port specification
        if parse.parse('{}:{}@{}', formatted_string) is not None:
            return list(parse.parse('{}:{}@{}', formatted_string)) + [5432]
    return None
