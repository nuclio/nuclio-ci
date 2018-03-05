import pg8000

PGUSERNAME = "postgres"
PGPASSWORD = "pass"
PGHOST = "172.17.0.1"

def handler(context, event):

    # connect to postgres database
    conn = pg8000.connect(host=PGHOST, user=PGUSERNAME, password=PGPASSWORD)

    # get data to insert
    git_slack_usernames = event.body[0]
    context.logger.info(data)
    context.logger.info(git_slack_usernames)

    conn.cursor().execute("insert into users (github_username, slack_username) values ({});".format(pair_of_user for pair_of_user in git_slack_usernames))
    conn.commit()

    return 'ok'
