import os
import argparse
import delegator
import json


def _run(command, block=True, binary=False, timeout=None, cwd=None, env=None, allow_error=False):
    _log('Running command', cmd=command)

    result = delegator.run(command, block, binary, timeout=None, cwd=cwd, env=env)

    if result.return_code != 0 and not allow_error:
        raise RuntimeError(f'Command failed:\n{command}\n{result.out}\n{result.err}')


def _log(format, *args, **kw_args):
    output = format

    if kw_args:
        output += ': ' + str(kw_args)

    print(output)


# TODO : fit into nuclio-ci vars & functions
def _get_functions(host):

    return {
        'gatekeeper': {
            'env': {'REPO_OWNER_DETAILS': os.environ.get('repo_owner_details'),
                    'PGINFO': 'postgres:pass@172.17.0.1:5432'},  # username:access_token,
            'port': 12345,
            'path': '/gatekeeper',
            'build-command': 'pip install requests parse'
        },
        'database_init': {
            'env': {'PGINFO': 'postgres:pass@172.17.0.1:5432'},
            'port': 36543,
            'path': '/database_init',
            'volume': "/var/run/docker.sock:/var/run/docker.sock",
            'build-command': "export PATH=$PATH:/usr/local/go/bin && apt-get update && apt-get install -y git \
                 && apt-get install -y build-essential && curl -O https://download.docker.com/linux/static/stable/x86_64/docker-18.03.0-ce.tgz \
                 && tar xzvf docker-18.03.0-ce.tgz\
                 && cp docker/* /usr/bin/\
                 && curl -O https://dl.google.com/go/go1.9.5.linux-amd64.tar.gz\
                 && tar -C /usr/local -xzf go1.9.5.linux-amd64.tar.gz\
                 && mkdir -p /root/go/src/github.com/nuclio/nuclio && go get github.com/v3io/v3io-go-http/...\
                 && go get github.com/nuclio/logger/... && go get github.com/nuclio/nuclio-sdk-go/... && go get github.com/nuclio/amqp/... && " \
                             "pip install parse delegator.py psycopg2"
        },
        'github_status_updater': {
            'env': {'REPO_OWNER_USERNAME': 'some_repo_owner_username',
                    'REPO_OWNER_OAUTH_TOKEN': 'some_repo_owner_oauth_token'},
            'port': 36544,
            'path': '/github_status_updater',
            'build-command': 'pip install requests'
        },
        'release_node': {
            'env': {'PGINFO': 'postgres:pass@172.17.0.1:5432'},
            'port': 36550,
            'path': '/release_node',
            'build-command': 'apk add --update --no-cache gcc musl-dev python-dev postgresql-dev & pip install psycopg2 parse requests'
        },
        'run_job': {
            'port': 36548,
            'env': {'PGINFO': 'postgres:pass@172.17.0.1:5432'},
            'path': '/run_job',
            'build-command': 'apk add --update --no-cache gcc python-dev musl-dev postgresql-dev docker '
                              'pip install psycopg2 parse requests'
        },
        'run_test_case': {
            'build-command': 'apk add --update --no-cache gcc musl-dev python-dev postgresql-dev docker '
                              'pip install delegator.py psycopg2 requests parse',
            'port': 36547,
            'env': {'PGINFO': 'postgres:pass@172.17.0.1:5432'},
            'path': '/run_test_case'
        },
        'build_push_artifacts': {
            'env': {'HOST_URL': 'localhost:5000', 'DOCKERIZED_BUILD': 'TRUE', 'GOPATH': '/root/go', 'NUCLIO_PATH':
                  '/root/go/src/github.com/nuclio/nuclio'},
            'build-command': 'export PATH=$PATH:/usr/local/go/bin && apt-get update && apt-get install -y git'
         '&& apt-get install -y build-essential && curl -O https://download.docker.com/linux/static/stable/x86_64/docker-18.03.0-ce.tgz'
         '&& tar xzvf docker-18.03.0-ce.tgz'
         '&& cp docker/* /usr/bin/'
         '&& curl -O https://dl.google.com/go/go1.9.5.linux-amd64.tar.gz'
         '&& tar -C /usr/local -xzf go1.9.5.linux-amd64.tar.gz'
         '&& mkdir -p /root/go/src/github.com/nuclio/nuclio && go get github.com/v3io/v3io-go-http/...'
         '&& go get github.com/nuclio/logger/... && go get github.com/nuclio/nuclio-sdk-go/... && go get github.com/nuclio/amqp/... ',
            'port': 36546,
            'volume': "/var/run/docker.sock:/var/run/docker.sock",
            'path': '/build_push_artifacts'

        },
        'slack_notifier': {
            'build-command': 'pip install requests slackclient',
            'env': {'PGINFO': 'postgres:pass@172.17.0.1:5432'},
            'port': 36545,
            'path': '/slack_notifier'
        },
        'test_complete': {
            'build-command': 'apk add --update --no-cache gcc musl-dev python-dev postgresql-dev docker'
                              'pip install psycopg2 parse requests',
            'env': {'PGINFO': 'postgres:pass@172.17.0.1:5432'},
            'port': 36549,
            'path': '/test_complete'
        },
    }


def _format_function_env(env):
    return ' '.join(['--env {0}={1}'.format(key, value) for key, value in env.items()])


def _function_dir_to_function_name(function_dir):
    return function_dir.replace('_', '-')


def _get_function_parameters(function_configuration):
    formatted_env_parameter = _format_function_env(function_configuration.get('env'))

    nuctl_parameters = [
        'build-command', 'volume'
    ]
    stringed_parameters = [
        'build-command'
    ]

    parameters = ''
    for parameter in nuctl_parameters:
        parameter_value = function_configuration.get(parameter)
        if parameter_value is not None:
            parameters += f" --{parameter} " + \
                          (f'"{parameter_value}"' if parameter in stringed_parameters else f'"{parameter_value}"')

    return formatted_env_parameter + parameters


def _deploy_local(host):
    network_name = 'zandbox-network'

    # first, delete all running function containers
    _log('Removing functions')

    for function_dir in _get_functions(host).keys():
        _run(f'docker rm -f default-{_function_dir_to_function_name(function_dir)}', allow_error=True)

    # remove the zandbox local network
    _log('Removing network')
    _run(f'docker network rm {network_name}', allow_error=True)

    # create a zandbox local network so that functions can communicate
    _log('Creating network')
    _log('Creating network')
    _run(f'docker network create {network_name}')

    # deploy all the functions
    for function_dir, function_configuration in _get_functions(host).items():

        function_name = _function_dir_to_function_name(function_dir)

        http_trigger = json.dumps({
            'ht': {
                'kind': 'http',
                'attributes': {
                    'numWorkers': 8,
                    'port': function_configuration['port']
                }
            }
        })

        command_formatted_properties = f'nuctl deploy {function_name} ' \
                                       '--runtime python:3.6 ' \
                                       '--run-image zandbox:latest ' \
                                       f'--handler functions.{function_dir}.{function_dir}:handler ' \
                                       f'--verbose '

        parameters = _get_function_parameters(function_configuration)

        _run(command_formatted_properties + parameters + f" --platform local --triggers '{http_trigger}'")

        _run(f'docker network connect {network_name} default-{function_name}')


def _deploy_k8s(run_registry, host):

    # first, delete all running function containers
    _log('Removing functions')

    for function_dir in _get_functions(host).keys():
        _run(f'nuctl delete function -n nuclio {_function_dir_to_function_name(function_dir)}', allow_error=True)

    # deploy all the functions
    for function_dir, function_configuration in _get_functions(host).items():
        formatted_function_env = _format_function_env(function_configuration['env'])
        function_name = _function_dir_to_function_name(function_dir)

        http_trigger = {
            'ht': {
                'kind': 'http',
                'annotations': {
                    'traefik.frontend.rule.type': 'PathPrefixStrip'
                },
                'attributes': {
                    'port': function_configuration['port']
                }
            }
        }

        if 'path' in function_configuration:
            http_trigger['ht']['attributes']['ingresses'] = {
                'web': {
                    'host': '',
                    'paths': ['/api' + function_configuration['path']]
                }
            }

        _run('nuctl deploy '
             f'--run-image zandbox:latest '
             f'--handler functions.{function_dir}.{function_dir}:handler '
             '--runtime python:3.6 '
             f'{formatted_function_env} '
             f'{function_name} '
             f'--verbose '
             '--replicas 1 '
             '--namespace nuclio '
             f'--run-registry {run_registry} '
             f"--triggers '{json.dumps(http_trigger)}'")


if __name__ == '__main__':

    # create argument parser
    parser = argparse.ArgumentParser(description=__doc__)

    # add arguments
    parser.add_argument('--platform', choices=['local', 'kube'], default='local')
    parser.add_argument('--run-registry', type=str)
    parser.add_argument('--host', type=str, required=True)

    # parse the arguments
    args = parser.parse_args()
    print(str(args))
    # now do the deploy
    if args.platform == 'local':
        _deploy_local(args.host)
    else:
        _deploy_k8s(args.run_registry, args.host)
