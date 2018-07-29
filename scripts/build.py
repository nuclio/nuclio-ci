import os
import delegator
import argparse


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


def build_image(push_registry):
    project_root_dir = os.path.dirname(os.path.realpath(__file__))

    print('Building ...')
    _run('docker build --no-cache -t zandbox .', cwd=os.path.join(project_root_dir, '..'))

    if push_registry:
        print(f'Pushing to {push_registry}')

        remote_image = f'{push_registry}/zandbox:latest'

        _run(f'docker tag zandbox:latest {remote_image}')
        _run(f'docker push {remote_image}')

    print('Done')


if __name__ == '__main__':

    # create argument parser
    parser = argparse.ArgumentParser(description=__doc__)

    # add arguments
    parser.add_argument('--push-registry', type=str)

    # parse the arguments
    args = parser.parse_args()

    build_image(args.push_registry)
