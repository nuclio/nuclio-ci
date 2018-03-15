import psycopg2
import os


# gets nothing in event.body
def handler(context, event):

    # get postgres connection information from container's environment vars
    postgres_host = os.environ.get('PGHOST')
    postgres_user = os.environ.get('PGUSERNAME')
    postgres_password = os.environ.get('PGPASSWORD')
    postgres_port = os.environ.get('PGPORT')
    users = os.environ.get('USERS')

    # raise NameError if env var not found
    if not (postgres_host and postgres_user and postgres_password and postgres_port and users):
        raise NameError('Local variable PGUSERNAME, PGPASSWORD, PGHOST, PGPORT or USERS could not be found')

    # connect to postgres database,
    conn = psycopg2.connect(host=postgres_host, user=postgres_user, password=postgres_password, port=postgres_port)

    # get usernames to insert
    git_slack_usernames = users.split('_')

    # get every even and odd user together, to insert properly in users table
    users = [(git_slack_usernames[i], git_slack_usernames[i + 1]) for i in range(0, len(git_slack_usernames), 2)]

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
