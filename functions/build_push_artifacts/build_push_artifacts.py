import os
import parse
import libs.common.nuclio_helper_functions

NUCLIO_PATH = os.environ.get('NUCLIO_PATH')
LOCAL_ARCH = 'amd64'


# get build git_url, optional git_branch & git_commit in event.body
# returns image_tags if images in the local registry
def handler(context, event):

    # get vars for building and pushing the artifacts

    request_body = event.body

    context.logger.debug(request_body)

    registry_host_and_port = os.environ.get('HOST_URL', '172.17.0.1:5000')
    git_url = request_body.get('git_url')
    git_commit = request_body.get('git_commit')
    git_branch = request_body.get('git_branch')

    # check, if git_url (required var) is not given, raise NameError
    if None in [git_url, git_commit, git_branch]:
        raise NameError('Not all requested inputs (git_url, git_commit, git_branch) could be found')

    # clone given repo with git clone repo-url
    clone_repo(context, git_url)

    # building repo with checkout branch / commit and make build
    build_repo(context, git_branch, git_commit)

    # get images tags
    images_tags = get_images_tags(context)

    # tag and push images, update images_tags to names pushed to local registry
    artifact_urls = push_images(context, images_tags, registry_host_and_port)

    # build and push tester image
    build_push_tester_image(context, registry_host_and_port, git_branch, git_commit)

    tests_paths = _get_tests_paths(context)

    # clean directory
    libs.common.nuclio_helper_functions.run_command(context, 'rm -r  /root/go/src/github.com/nuclio/nuclio', '/')

    context.logger.debug(context.Response(body={'artifact_urls': artifact_urls, 'tests_paths': tests_paths}))
    return context.Response(body={'artifact_urls': artifact_urls, 'tests_paths': tests_paths})


# clone given git_url
def clone_repo(context, git_url):

    # git clone given repository
    git_url = 'https://github.com/ilaykav/nuclio.git'
    libs.common.nuclio_helper_functions.run_command(context, f'git clone {git_url} {NUCLIO_PATH}', '/')


# checkout git_branch then git_commit & build
def build_repo(context, git_branch, git_commit):

    # checkout to branch & commit if given
    # for checkout_value in [git_branch, git_commit]: common.nuclio_helper_functions.run_command(context, 'checkout {checkout_value}', NUCLIO_PATH)
    # get tests-paths, `git checkout nuclio-ci-tmp-test-branch` is hardcoded until merging with dev
    libs.common.nuclio_helper_functions.run_command(context, f'git checkout nuclio-ci-tmp-test-branch', NUCLIO_PATH)

    # build artifacts
    libs.common.nuclio_helper_functions.run_command(context, 'export PATH=$PATH:/usr/local/go/bin && make build', NUCLIO_PATH)


# get all images tags, based on option make print-docker-images in MakeFile
def get_images_tags(context):

    # get all docker images
    images = libs.common.nuclio_helper_functions.run_command(context, 'make print-docker-images', NUCLIO_PATH).split('\n')

    # filter out all non-paths, comments and commands, etc.
    return list(filter(lambda path: path[:6] == 'nuclio', images))


# get image tags, tag the images with tag fit local registry push convention and push to given registry_host_and_port
def push_images(context, images_tags, registry_host_and_port):

    # iterate over all images_tags, tag each one for pushing to localhost, and return new tags of images_tags
    for image_index, image in enumerate(images_tags):

            # parse result
            registry_name, image_tag = parse_docker_image_name(image)

            # make new image tag, in format of registry_host_and_port/tag_of_image
            new_image_tag = f'{registry_host_and_port}/{image_tag}{LOCAL_ARCH}'

            # tag image with new image tag, relevant for pushing to local registry, log tag result
            libs.common.nuclio_helper_functions.run_command(context, f'docker tag {image} {new_image_tag}', '/')

            # push with the new image tag to local registry, log push result
            libs.common.nuclio_helper_functions.run_command(context, f'docker push {new_image_tag}', '/')

            # change image to its new tag values
            images_tags[image_index] = new_image_tag

    return images_tags


# build and push tester image, necessary for running tests
def build_push_tester_image(context, registry_host_and_port, git_branch, git_commit):

    # make new image tag, in format of registry_host_and_port/tag_of_image
    tester_tag = f'{registry_host_and_port}/tester:latest-{LOCAL_ARCH}'

    # get tests-paths, `git checkout nuclio-ci-tmp-test-branch` is hardcoded until merging with dev
    libs.common.nuclio_helper_functions.run_command(context,
                'git checkout nuclio-ci-tmp-test-branch',
                                                    NUCLIO_PATH)

    # until merge with dev, then it will be-
    # for checkout_value in [git_branch, git_commit]:
    # common.nuclio_helper_functions.common.nuclio_helper_functions.run_command(context, f'git checkout {checkout_value}', NUCLIO_PATH)

    # build tester
    libs.common.nuclio_helper_functions.run_command(context, f'docker build --file nuclio/test/docker/tester/Dockerfile --tag {tester_tag} .',
                '/root/go/src/github.com/nuclio')

    # push with the new image tag to local registry, log push result
    libs.common.nuclio_helper_functions.run_command(context, f'docker push {tester_tag}', '/')

    # return tester-tag
    return tester_tag


# returns parsed values- registry_name and image_tag of given input
def parse_docker_image_name(parse_input):
    parse_result = parse.parse('{}/{}', parse_input)

    # raise NameError if image parse was unsuccessful
    if parse_result is None:
        raise NameError(f'Image tag {parse_input} is not in format of nuclio/tag-of-image')

    return list(parse_result)


def _get_tests_paths(context):
    tests_paths = libs.common.nuclio_helper_functions.run_command(context,
                'git checkout nuclio-ci-tmp-test-branch && export PATH=$PATH:/usr/local/go/bin && '
                'make print-tests-paths',
                                                                  NUCLIO_PATH).split('\n')

    # filter out all non-paths, comments and commands, etc.
    return list(filter(lambda path: path[:3] == 'pkg', tests_paths))
