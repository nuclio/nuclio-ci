import json
import os
import parse
import delegator

NUCLIO_PATH = '/root/go/src/github.com/nuclio/nuclio'
LOCAL_ARCH = 'amd64'


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
    for input_value in [git_url, git_commit, git_branch]:
        if input_value is None:
            raise NameError('Not all requested inputs (git_url, git_commit, git_branch) could be found')

    # clone given repo with git clone repo-url
    clone_repo(context, git_url)
    context.logger.info('Successfully finished cloning repository')

    # building repo with checkout branch / commit and make build
    build_repo(context, git_branch, git_commit)
    context.logger.info('Successfully finished building repository')

    # get images tags
    images_tags = get_images_tags(context)
    context.logger.info('Successfully resolved images tags')

    # tag and push images, update images_tags to names pushed to local registry
    images_tags = push_images(context, images_tags, registry_host_and_port)
    context.logger.info('Successfully finished tagging and pushing images')

    return context.Response(body=images_tags)


# clone given git_url
def clone_repo(context, git_url):

    # make directory for git, init git, and clone given repository
    run_command(context, f'export PATH=$PATH:/usr/local/go/bin && export GOPATH=/root/go \
    && curl -O https://download.docker.com/linux/static/stable/x86_64/docker-18.03.0-ce.tgz \
    && tar xzvf docker-18.03.0-ce.tgz \
    && cp docker/* /usr/bin/ \
    && curl -O https://dl.google.com/go/go1.9.5.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go1.9.5.linux-amd64.tar.gz \
    && mkdir -p $GOPATH \
    && cd $GOPATH \
    && git clone {git_url} $GOPATH/src/github.com/nuclio/nuclio', '/tmp')


# checkout git_branch then git_commit & build
def build_repo(context, git_branch, git_commit):

    # checkout to branch & commit if given
    for checkout_value in [git_branch, git_commit]:
        run_command(context, f'git checkout {checkout_value}', NUCLIO_PATH)

    # build artifacts
    run_command(context, 'export PATH=$PATH:/usr/local/go/bin && export GOPATH=/root/go \
    && go get github.com/v3io/v3io-go-http/... \
    && go get github.com/nuclio/logger/... \
    && go get github.com/nuclio/nuclio-sdk-go/... \
    && go get github.com/nuclio/amqp/... \
    && echo $PATH && echo $GOPATH && make build', NUCLIO_PATH)


# get all images tags, based on option make print-docker-images in MakeFile
def get_images_tags(context):

    # get all docker images
    images = run_command(context, 'make print-docker-images', NUCLIO_PATH)

    # convert response to list by splitting all \n
    return images.split('\n')


# get image tags, tag the images with tag fit local registry push convention and push to given registry_host_and_port
def push_images(context, images_tags, registry_host_and_port):

    # iterate over all images_tags, tag each one for pushing to localhost, and return new tags of images_tags
    for image_index, image in enumerate(images_tags):

            # skip env-declaring PATH to get arch by using own arch
            image += LOCAL_ARCH

            # parse result
            parse_result = parse.parse('{}/{}', image)

            # raise NameError if image parse was unsuccessful
            if parse_result is None:
                raise NameError(f'Image tag {image} is not in format of nuclio/tag-of-image')

            # make new image tag, in format of registry_host_and_port/tag_of_image
            new_image_tag = f'{registry_host_and_port}/{list(parse_result)[1]}'

            # tag image with new image tag, relevant for pushing to local registry, log tag result
            tag_result = run_command(context, f'docker tag {image} {new_image_tag}', '/')
            context.logger.info_with('Tagged image finished', Tag_result=tag_result)

            # push with the new image tag to local registry, log push result
            push_result = run_command(context, f'docker push {new_image_tag}', '/')
            context.logger.info_with('Pushed image finished', Push_result=push_result)

            # change image to its new tag values
            images_tags[image_index] = new_image_tag
    return images_tags


# get env in map format {"key1":"value1"}
def run_command(context, cmd, cwd=None, env=None):

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
    if proc.return_code != 0:
        raise ValueError(f'Command failed. cmd({cmd}) result({proc.return_code}), log({proc.out})')

    return proc.out
