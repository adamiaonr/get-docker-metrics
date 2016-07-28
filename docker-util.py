import os
import pwd
import subprocess as subprocess
import argparse

KOLLA_GIT_REPO_DIR = "~/workbench/kolla"
KOLLA_DEPLOYMENT_DIR = "/usr/local/share/kolla"
KOLLA_BIN_DIR = "/usr/local/bin"

DOCKER_REGISTRY_DEFAULT_HOST = "registry.local"
DOCKER_REGISTRY_DIR = "/data/registry/docker/registry/v2/repositories"

DOCKER_CONTAINER_STOP = "stop"
DOCKER_CONTAINER_REMOVE = "rm"
DOCKER_CONTAINER_ACTIONS = [ DOCKER_CONTAINER_STOP, DOCKER_CONTAINER_REMOVE ]

DOCKER_IMAGE_REMOVE = "rmi"
DOCKER_IMAGE_ACTIONS = [ DOCKER_IMAGE_REMOVE ]

def get_username():
    return pwd.getpwuid( os.getuid() )[ 0 ]

def run_command(command):

    try:
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

def docker_list_repo(host, repo_name):

    if (not host):
        host = DOCKER_REGISTRY_DEFAULT_HOST

    command = "ssh " + get_username() + "@" + host \
        + " \"cd " + DOCKER_REGISTRY_DIR + "; ls "
    # if a repo_name is specified, append it to the command
    if (repo_name):
        command = command + " | grep " + repo_name \
        + " | awk \'{print $9}\' | xargs --no-run-if-empty ls"

    command = command + "\""

    return run_command(command)

def docker_remove_repo(host, repo_name):

    if (not host):
        host = DOCKER_REGISTRY_DEFAULT_HOST

    if (not repo_name):
        return

    command = "ssh " + get_username() + "@" + host \
        + " sudo rm -rfv " + DOCKER_REGISTRY_DIR + "/" + repo_name

    return run_command(command)

def docker_container_action(action, pattern):

    if action in DOCKER_CONTAINER_ACTIONS:
        command = "docker ps -a | grep " \
            + pattern \
            + " | awk '{print $1}' | xargs --no-run-if-empty docker " + action
        return run_command(command)

    sys.stderr.write(
            """docker-util::act_on_containers() : [ERROR] not a valid docker 
            action: %s\n""" \
            % (action)) 

    return

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
        "--docker-list-repo", 
         help = """[ACTION] lists entries in a docker repo, kept in a docker 
                registry. e.g. '$ python docker-util.py --docker-list-repo --host 
                192.168.8.19 --pattern \"kolla\"' lists all entries in a 
                repository with name 'kolla', kept in a private registry 
                located on host 192.168.8.19.""",
                action = "store_true")

    parser.add_argument(
        "--docker-remove-repo", 
         help = """[ACTION] removes an entry in a docker 
                registry. e.g. '$ python docker-util.py --docker-remove-repo 
                --host 192.168.8.19 --pattern \"openstack-kolla/apt-cacher-ng\"' 
                removes the docker image 'apt-cache-ng' in a repo named 
                'openstack-kolla'. the whole 'openstack-kolla' repo can be removed 
                by specifying '--pattern \"openstack-kolla\"'. the '--pattern' 
                option must be the precise name of a dir, otherwise the command 
                won't run.""",
                action = "store_true")

    parser.add_argument("--docker-stop", 
         help = """[ACTION] stop one (or more) docker container(s). e.g. '$ python 
                docker-util.py --docker-stop --pattern \"kolla\"' stops all 
                docker containers whose 'NAME' includes the word 'kolla'.""",
                action = "store_true")

    parser.add_argument("--pattern", 
         help = """[ARG] pattern to apply to the command. meaning depends on the 
                command""")

    parser.add_argument("--host", 
         help = """[ARG] host to apply to the command. applicability depends on the 
                command. if not applicable, option is ignored.""")

    args = parser.parse_args()
    print args

    # get the action
    if (args.docker_stop):

        docker_container_action(DOCKER_CONTAINER_STOP, args.pattern)

    elif (args.docker_list_repo):

        print(docker_list_repo(args.host, args.pattern).rstrip())

    elif (args.docker_remove_repo):

        print(docker_remove_repo(args.host, args.pattern).rstrip())

    else:

        sys.stderr.write("""docker-util::main(): [ERROR] not a valid docker 
            action\n""") 
        parser.print_help()

        sys.exit(1)

