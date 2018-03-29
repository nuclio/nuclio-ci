import json
import os
import parse
import delegator


# get build git_url, optional git_branch & git_commit in event.body
# returns image_tags if images in the local registry
def handler(context, event):

    # get vars for building and pushing the artifacts
    request_body = json.loads(event.body)
    registry_host_and_port = os.environ.get('HOST_URL', '172.17.0.1:5000')
    git_url = request_body.get('git_url')
    git_commit = request_body.get('git_commit')
    git_branch = request_body.get('git_branch')

    # check, if git_url (required var) is not given, raise NameError
    if git_url is None:
        raise NameError('Local variable NUCLIO_CI_SLACK_TOKEN could not be found')

    # clone given repo with git clone repo-url, checkout branch / commit if necessary and make build
    clone_and_build_repo(context, git_branch, git_commit, git_url)
    context.logger.info('Successfully finished building repository')

    # get images tags
    images_tags = get_images_tags(context)
    context.logger.info('Successfully resolved images tags')

    # tag and push images, update images_tags to names pushed to local registry
    images_tags = tag_and_push_images_to_local_registry(context, images_tags, registry_host_and_port)
    context.logger.info('Successfully finished tagging and pushing images')

    return images_tags


# clone given git_url, checkouts to git_branch then git_commit if given
def clone_and_build_repo(context, git_branch, git_commit=None, git_url=None):

    # make directory for git, init git, and clone given repository
    run_command(context, 'mkdir -p  /go/src/github.com/nuclio', '/')

    run_command(context, 'git init && git clone {0}'.format(git_url), '/go/src/github.com/nuclio')


    run_command(context, 'git clone https://github.com/v3io/v3io-go-http', '/go/src/github.com/nuclio')
    run_command(context, 'mv v3io-go-http v3io', '/go/src/github.com/nuclio')

    run_command(context, 'git clone https://github.com/nuclio/logger.git', '/go/src/github.com/nuclio')
    run_command(context, 'git clone https://github.com/nuclio/nuclio-sdk-go.git', '/go/src/github.com/nuclio')
    run_command(context, 'git clone https://github.com/nuclio/nuclio-sdk.git', '/go/src/github.com/nuclio')

    run_command(context, 'go get github.com/nuclio/amqp/...', '/go/src/github.com/nuclio')
    run_command(context, 'go get github.com/nuclio/nuclio-sdk-go/...', '/go/src/github.com/nuclio')
    run_command(context, 'go get github.com/nuclio/logger/...', '/go/src/github.com/nuclio')
    run_command(context, 'go get -d github.com/nuclio/v3io/...', '/go/src/github.com/nuclio')

    # checkout to branch & commit if given
    for checkout_value in [git_branch, git_commit]:
        if checkout_value is not None:
            run_command(context, 'git checkout {0}'.format(checkout_value), '/go/src/github.com/nuclio/nuclio')

    # build artifacts
    run_command(context, 'make build', '/go/src/github.com/nuclio/nuclio')


# get all images tags, based on option make print-docker-images in MakeFile
def get_images_tags(context):

    # get all docker images, parse response
    images = parse.parse('{}done{}',
                         run_command(context, 'make print-docker-images', '/go/nuclio/src/github.com/nuclio/nuclio'))

    # raise ValueError if parse failed
    if images is None:
        raise ValueError('Could not parse images in format of \'{}done{}\'')

    # convert parse response to list, get second var from list (images), split by \n->['', 'image_name1', 'image_name2']
    images = list(images)[1].split('\n')

    # remove empty image_tags in case of first / double '\n' -> ['image_name1', 'image_name2']
    return list(filter(lambda image_tag: bool(image_tag), images))


# get image tags, tag the images with tag fit local registry push convention and push to given registry_host_and_port
def tag_and_push_images_to_local_registry(context, images_tags, registry_host_and_port):

    # iterate over all images_tags, tag each one for pushing to localhost, and return new tags of images_tags
    for image_index, image in enumerate(images_tags):
            parse_result = parse.parse('{}/{}', image)

            # raise NameError if image parse was unsuccessful
            if parse_result is None:
                raise NameError('Image tag {0} is not in format of nuclio/tag-of-image '.format(image))

            # make new image tag, in format of registry_host_and_port/tag_of_image
            new_image_tag = '{0}/{1}'.format(registry_host_and_port, list(parse_result)[1])

            # tag image with new image tag, relevant for pushing to local registry, log tag result
            tag_result = run_command(context, 'docker tag {0} {1}'.format(image, new_image_tag), '/')
            context.logger.info_with('Tagged image finished', Tag_result=tag_result)

            # push with the new image tag to local registry, log push result
            push_result = run_command(context, 'docker push {0}'.format(new_image_tag), '/')
            context.logger.info_with('Pushed image finished', Push_result=push_result)

            # change image to its new tag values
            images_tags[image_index] = new_image_tag
    return images_tags


# get env in map format {"key1":"value1"}
def run_command(context, cmd, cwd=None, timeout=None, env=None):

    context.logger.info_with('Running command', cmd=cmd, cwd=cwd, env=env)

    os_environ_copy = os.environ.copy()

    if env is not None:
        for key in env:
            del os_environ_copy[key]
        env.update(os_environ_copy)
    else:
        env = os_environ_copy

    if cwd is not None:
        cmd = 'cd {0} && {1}'.format(cwd, cmd)

    proc = delegator.run(cmd, env=env)

    # if we got here, the process completed
    if proc.return_code != 0:
        raise ValueError('Command failed. cmd({0}) result({1}), log({2})'.format(cmd,
                                                                                 proc.return_code,
                                                                                 proc.out))

    return proc.out

