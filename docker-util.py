#!/usr/bin/env python

import os
import sys
import pwd
import subprocess as subprocess
import argparse

TERMINAL_CMD = "uxterm -e"

KOLLA_GIT_REPO_DIR = "~/workbench/kolla"
KOLLA_DEPLOYMENT_DIR = "/usr/local/share/kolla"
KOLLA_BIN_DIR = "/usr/local/bin"

DOCKER_REGISTRY_DEFAULT_HOST = "registry.local"
DOCKER_REGISTRY_DIR = "/data/registry/docker/registry/v2/repositories"

DOCKER_CONTAINER_STOP = "stop"
DOCKER_CONTAINER_REMOVE = "rm"
DOCKER_CONTAINER_REMOVE_IMAGE = "rmi"
DOCKER_CONTAINER_RUN = "run"
DOCKER_CONTAINER_ACTIONS = [ DOCKER_CONTAINER_STOP, \
                            DOCKER_CONTAINER_REMOVE, \
                            DOCKER_CONTAINER_REMOVE_IMAGE, \
                            DOCKER_CONTAINER_RUN ]

DOCKER_IMAGE_REMOVE = "rmi"
DOCKER_IMAGE_ACTIONS = [ DOCKER_IMAGE_REMOVE ]

def get_username():
    return pwd.getpwuid( os.getuid() )[ 0 ]

def run_command(command, no_wait=False):

    try:

        if (no_wait):
            p = subprocess.Popen(
                [command], 
                shell = True, 
                stdin = None, stdout = None, stderr = None, close_fds = True)

        else:
            p = subprocess.Popen(
                [command], 
                stdout = subprocess.PIPE,
                shell = True)
            p.wait()

        (result, error) = p.communicate()
        
    except subprocess.CalledProcessError as e:
        sys.stderr.write(
            "docker-util::run_command() : [ERROR]: output = %s, error code = %s\n" 
            % (e.output, e.returncode))

    return result

def docker_ls_repo(host, patterns):

    if (not host):
        host = DOCKER_REGISTRY_DEFAULT_HOST

    command = "ssh " + get_username() + "@" + host \
        + " \"cd " + DOCKER_REGISTRY_DIR + "; ls "

    # if patterns are specified, append them to the command as 'grep'
    if (len(patterns)):
        for pattern in patterns:
            command = command + " | grep " + pattern
        command = command + " | awk \'{print $9}\' | xargs --no-run-if-empty ls"

    command = command + "\""
    return run_command(command)

def docker_rm_repo(host, patterns):

    if (not host):
        host = DOCKER_REGISTRY_DEFAULT_HOST

    if (len(patterns) != 1):
        return

    command = "ssh " + get_username() + "@" + host \
        + " sudo rm -rfv " + DOCKER_REGISTRY_DIR + "/" + patterns[0]

    return run_command(command)

def docker_container_action(action, patterns):

    if (not len(patterns)):
        return

    no_wait = False

    if (action in [ DOCKER_CONTAINER_STOP, DOCKER_CONTAINER_REMOVE ]):
        command = "docker ps -a"

        for pattern in patterns:
            command = command + " | grep " + pattern

        command = command + " | awk '{print $1}'" \
            + " | xargs --no-run-if-empty docker " + action

    elif (action == DOCKER_CONTAINER_REMOVE_IMAGE):
        command = "docker images "

        for pattern in patterns:
            command = command + " | grep " + pattern

        command = command + " | awk '{print $1\":\"$2}'" \
            + " | xargs --no-run-if-empty docker " + action

    elif (action == DOCKER_CONTAINER_RUN):
        command = "docker images"

        for pattern in patterns:
            command = command + " | grep " + pattern

        command = command + " | awk \'{print $3}\'"
        container_id = run_command(command)

        if (len(container_id.rstrip().split("\n")) != 1):
            return

        command = TERMINAL_CMD + " 'docker run --rm -ti " + container_id.rstrip() + " bash' &"
        no_wait = True

    return run_command(command, no_wait)

def docker_image_remove(pattern):

    if (not pattern):
        return

    command = "docker images | grep " \
        + pattern \
        + " | awk '{print $1\":\"$2}' | xargs --no-run-if-empty docker rmi"

    return run_command(command)

#def cleanup_openstack_deployment():

#    # cleanup existing openstack deployments w/ kolla-ansible
#    print(run_command("kolla-ansible -vvv cleanup"))

#    # uninstall existing kolla installations
#    print(run_command("sudo -H pip uninstall " + KOLLA_GIT_REPO_DIR))
#    # remove contents in KOLLA_DEPLOYMENT_DIR
#    print(run_command("sudo rm -rf " + KOLLA_DEPLOYMENT_DIR))
#    # remove kolla-* executables
#    print(run_command("sudo rm -rf " + KOLLA_BIN_DIR + "/kolla-*"))

#    return

#def deploy_openstack_kolla(version):

#    # cleanup a previous openstack deployment
#    cleanup_openstack_deployment()

#    # checkout the git revision of the openstack-kolla-* version to 
#    # deploy (this will only install kolla tools, not build anything)
#    

#    command = "docker images | grep " 
#        + pattern 
#        + " | awk '{print $1":"$2}' | xargs --no-run-if-empty docker rmi"
#    return run_command(command)

if __name__ == '__main__':

    # use an ArgumentParser for a nice CLI
    parser = argparse.ArgumentParser()

    # options (self-explanatory)
    parser.add_argument(
        "--docker-ls-repo", 
         help = """[ACTION] lists entries in a docker repo, kept in a docker 
                registry. e.g. '$ python docker-util.py --docker-ls-repo 
                --host 192.168.8.19 --pattern \"kolla\"' lists all entries in a 
                repository with name 'kolla', kept in a private registry 
                located on host 192.168.8.19.\n""",
                action = "store_true")

    parser.add_argument(
        "--docker-rm-repo", 
         help = """[ACTION] removes an entry in a docker 
                registry. e.g. '$ python docker-util.py --docker-rm-repo 
                --host 192.168.8.19 --pattern '\"openstack-kolla/apt-cacher-ng\"' 
                removes the docker image 'apt-cache-ng' in a repo named 
                'openstack-kolla'. the whole 'openstack-kolla' repo can be 
                removed by specifying '--pattern \"openstack-kolla\"'. the 
                '--pattern' option must be the precise name of a dir, otherwise 
                the command won't run.\n""",
                action = "store_true")

    parser.add_argument("--docker-stop", 
         help = """[ACTION] stop one (or more) docker container(s). e.g. 
                '$ python docker-util.py --docker-stop --pattern 
                \"kolla\"' stops all docker containers whose 'NAME' includes 
                the word 'kolla'.\n""",
                action = "store_true")

    parser.add_argument("--docker-rm", 
         help = """[ACTION] remove one (or more) docker container(s). e.g. 
                '$ python docker-util.py --docker-rm --pattern 
                \"kolla\"' removes all docker containers whose 'NAME' includes 
                the word 'kolla'.\n""",
                action = "store_true")

    parser.add_argument("--docker-rmi", 
         help = """[ACTION] remove one (or more) local docker images. e.g. 
                '$ python docker-util.py --docker-rmi --pattern 
                \"kolla\"' removes all local docker images whose 'NAME' includes 
                the word 'kolla'.\n""",
                action = "store_true")

    parser.add_argument("--docker-run", 
         help = """[ACTION] runs a test docker container, given part of the 
                name of an image. e.g. '$ python docker-util.py 
                --docker-run --pattern \"mitaka|swift-base\"' fetches 
                the id of the docker image w/ the terms 'mitaka' and 'swift-base' 
                in its name. if more than 1 id is fetched, the command doesn't run.\n""",
                action = "store_true")

    parser.add_argument("--pattern", 
         help = """[ARG] pattern(s) to apply to the command.multiple patterns 
                can be specified if separated with '|'. e.g. 
                '--pattern \"mitaka|swift-base\"' specifies 2 patterns: 
                'mitaka' and 'swift-base'. meaning depends on the command.\n""")

    parser.add_argument("--host", 
         help = """[ARG] host to apply to the command. applicability depends on 
                the command. if not applicable, option is ignored.\n""")

    args = parser.parse_args()

    # quit if not enough args
    if (len(sys.argv) < 2):
        sys.stderr.write("""docker-util::main(): [ERROR] no args supplied\n""") 
        parser.print_help()
        sys.exit(1)

    # extract the patterns
    patterns = args.pattern.split("|")

    # get the action
    if (args.docker_stop):
        docker_container_action(DOCKER_CONTAINER_STOP, patterns)

    elif (args.docker_rm):
        print(docker_container_action(DOCKER_CONTAINER_REMOVE, patterns).rstrip())

    elif (args.docker_rmi):
        print(docker_container_action(DOCKER_CONTAINER_REMOVE_IMAGE, patterns).rstrip())

    elif (args.docker_run):
        result = docker_container_action(DOCKER_CONTAINER_RUN, patterns)
        if (result):
            print result.rstrip()

    elif (args.docker_ls_repo):
        print(docker_ls_repo(args.host, patterns).rstrip())

    elif (args.docker_rm_repo):
        print(docker_rm_repo(args.host, patterns).rstrip())

    else:
        sys.stderr.write("""docker-util::main(): [ERROR] not a valid docker 
            action\n""") 
        parser.print_help()

        sys.exit(1)

