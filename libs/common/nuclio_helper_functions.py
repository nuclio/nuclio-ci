import requests
import os
import delegator


# calls given function with given arguments, returns body of response
def call_function(function_name, function_arguments=None):
    functions_ports = {
        'database_init': 31543,
        'github_status_updater': 31544,
        'slack_notifier': 31545,
        'build_and_push_artifacts': 31546,
        'run_test_case': 31547,
        'run_job': 31549,
        'test_case_complete': 31549,
        'release_node': 31550
    }

    # if given_host is specified post it instead of
    given_host = os.environ.get('DOCKER_HOST', '172.17.0.1')
    response = requests.post(f'http://{given_host}:{functions_ports[function_name]}',
                             data=function_arguments)

    return response.text


# get slack username from db according to given github_username
def convert_slack_username(db_cursor, github_username):

    # convert github username to slack username
    db_cursor.execute('select slack_username from users where github_username=%s', (github_username, ))

    # get slack username of given github username
    slack_username = db_cursor.fetchone()

    if slack_username is None:
        raise ValueError('Failed converting git username to slack username')

    # get first value of the postgresSQL tuple answer
    return slack_username[0]


# get env in map format {"key1":"value1"}
def run_command(context, cmd, cwd=None, env=None, accept_error=False):

    context.logger.info_with('Running command', cmd=cmd, cwd=cwd, env=env)

    os_environ_copy = os.environ.copy()

    if env is not None:
        for key in env:
            del os_environ_copy[key]
        env.update(os_environ_copy)
    else:
        env = os_environ_copy

    if cwd is not None:
        cmd = f'cd {cwd} && {cmd}'

    proc = delegator.run(cmd, env=env)

    # if we got here, the process completed
    if not accept_error and proc.return_code != 0:
        raise ValueError(f'Command failed. cmd({cmd}) result({proc.return_code}), log({proc.out})')

    # log result
    if proc.return_code == 0:
        context.logger.info_with('Command executed successfully', Command=cmd, Exit_code=proc.return_code, Stdout=proc.out)
    else:
        context.logger.info_with('Command failed', Command=cmd, Exit_code=proc.return_code, Stdout=proc.out)

    return proc.out
