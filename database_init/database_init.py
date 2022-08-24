# Copyright 2018 The Nuclio Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import psycopg2
import psycopg2.sql
import os
import json
import parse
import requests


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
                'create table jobs (state int, artifact_urls text) with oids',
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
            execute_using_parsed_arguments(cur, table, row_info)


# gets table name and row info (dict), execute command according to these given args
def execute_using_parsed_arguments(db_cursor, table_name, row_info):

    # {col1_name: col1_value, col2_name: col2_value} -> (col1_name, col2_name), ('col1_value', 'col2_value')
    db_cursor.execute(psycopg2.sql.SQL('insert into {0} ({1}) values ({2})').format(
        psycopg2.sql.SQL(table_name),
        psycopg2.sql.SQL(', ').join(map(psycopg2.sql.SQL, map(str, row_info.keys()))),
        psycopg2.sql.SQL(', ').join(map(psycopg2.sql.Literal, map(str, row_info.values())))
    ))


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
