import psycopg2
import os
import json
import parse
import functools


# init database, gets info to put in tanles in event.body in format of
# fixtures: { table_name: [{col1_name: col1_value, col2_name: col2_value...}, {col1_name...}] table_name2:...}
def handler(context, event):

    # get postgres connection information from container's environment vars
    postgres_info = parse_env_var_info(os.environ.get('PGINFO'))

    # raise NameError if env var not found, or found in wrong format
    if postgres_info is None:
        raise ValueError('Local variable PGINFO in proper format (user:password@host:port or user:password@host)'
                         ' could not be found')

    postgres_user, postgres_password, postgres_host, postgres_port = postgres_info

    # connect to postgres database,
    conn = psycopg2.connect(host=postgres_host, user=postgres_user, password=postgres_password, port=postgres_port)

    # proper commands to initialize database
    commands = ['create table test_cases (runnind_node oid, logs text, result int, job oid,'
                ' artifact_test text) with oids',
                'create table nodes (current_test_case oid) with oids',
                'create table jobs (state int) with oids',
                'create table users (github_username text, slack_username text) with oids']

    # cur is the cursor of current connection
    cur = conn.cursor()

    # iterate over commands, execute them with the cursor
    for command in commands:
        cur.execute(command)

    # process request - insert data accordingly
    process_request(json.loads(event.body)['fixtures'], conn)

    # commit changes
    conn.commit()


# gets string to process, return None if format is wrong, list of info if format is well writen -
# return-list : username, password, host, port
def parse_env_var_info(formatted_string):
    if formatted_string is not None:

        # check if default formatted string given
        if parse.parse('{}:{}@{}:{}', formatted_string) is not None:
            return list(parse.parse('{}:{}@{}:{}', formatted_string))

        # if not, try get same format without the port specification
        if parse.parse('{}:{}@{}', formatted_string) is not None:
            return list(parse.parse('{}:{}@{}', formatted_string)) + [5432]
    return None


# gets request's info and connection, inserts data
def process_request(request_json, database_connection):
    cur = database_connection.cursor()

    # insert data for every table in request
    for table in request_json:
        for row_info in request_json[table]:
            cur.execute(get_add_query(table, row_info))


# gets table name and row info (dict), returns insert query
def get_add_query(table_name, row_info):

    # {col1_name: col1_value, col2_name: col2_value} -> (col1_name, col2_name), ('col1_value', 'col2_value')
    return 'insert into {0} ({1}) values (\'{2}\')'.format(
        table_name,
        ', '.join(row_info.keys()),
        functools.reduce(lambda x, y: str(x) + '\', \'' + str(y), row_info.values())  # reduce + str() necessary because
                                                                                      # values may be not-strings
    )
