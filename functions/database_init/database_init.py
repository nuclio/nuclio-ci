import psycopg2.sql
import common.psycopg2_functions
import json


# init database, gets info to put in tanles in event.body in format of
# fixtures: { table_name: [{col1_name: col1_value, col2_name: col2_value...}, {col1_name...}] table_name2:...}
def handler(context, event):


    # proper commands to initialize database
    commands = ['create table test_cases (running_node oid, logs text, result text, job oid,'
                ' artifact_test text) with oids',
                'create table nodes (current_test_case oid) with oids',
                'create table jobs (state text, artifact_urls text, github_username text,'
                ' github_url text, commit_sha text) with oids',
                'create table users (github_username text, slack_username text) with oids']

    # cur is the cursor of current connection
    cur = context.user_data.conn.cursor()

    # iterate over commands, execute them with the cursor
    for command in commands:
        cur.execute(command)

    # process request - insert data accordingly
    process_request(json.loads(event.body)['fixtures'], context.user_data.conn)

    # commit changes
    context.user_data.conn.commit()

# gets request's info and connection, inserts data
def process_request(request_json, database_connection):
    cur = database_connection.cursor()

    # insert data for every table in request
    for table in request_json:
        for row_info in request_json[table]:
            execute_using_parsed_arguments(cur, table, row_info)


# gets table name and row info (dict), execute command according to these given args
def execute_using_parsed_arguments(db_cursor, table_name, row_info):

    # {col1_name: col1_value, col2_name: col2_value} -> (col1_name, col2_name), ('col1_value', 'col2_value')
    db_cursor.execute(psycopg2.sql.SQL('insert into {0} ({1}) values ({2})').format(
        psycopg2.sql.SQL(table_name),
        psycopg2.sql.SQL(', ').join(map(psycopg2.sql.SQL, map(str, row_info.keys()))),
        psycopg2.sql.SQL(', ').join(map(psycopg2.sql.Literal, map(str, row_info.values())))
    ))


def init_context(context):
    setattr(context.user_data, 'conn', common.psycopg2_functions.get_psycopg2_connection())
