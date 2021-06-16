import subprocess
import os
from deploy_config import BASE_DIR, BRANCH_BASE
import pkg_resources
from pkg_resources import VersionConflict
import sys


# None -> None
def pull_masters(repos):
    for repo in repos:
        chdir_repo(repo)
        subprocess.call('git pull origin master', shell=True)
        chdir_base()


# String -> None
def chdir_repo(repo):
    os.chdir(os.path.join(BASE_DIR, repo))


# None -> None
def chdir_base():
    os.chdir(BASE_DIR)


# None -> Boolean
def unstaged_changes_present(repos):
    for repo in repos:
        chdir_repo(repo)
        cmd = "git status -s | sed '/^??/d'"
        cmd_result = subprocess.check_output(cmd, shell=True)
        if b'' != cmd_result:
            return True
        chdir_base()
    return False


# String -> Boolean
def branch_exists_in_repos(branch_name, repos):
    for x in [branch_exists(repo, branch_name) for repo in repos]:
        if x:
            return True
    return False


# String String -> Boolean
def branch_exists(child_directory, branch_name):
    """
    Check if branch exists on remote server. Doesn't check locally
    """
    chdir_repo(child_directory)
    try:
        git_command = 'git ls-remote origin {}'.format(branch_name)
        result = subprocess.check_output(git_command, shell=True)
        return str(result).find('refs/heads/{}'.format(branch_name)) != -1
    except subprocess.CalledProcessError:
        return False
    finally:
        chdir_base()


# String -> None
def print_with_newlines(msg):
    for line in msg.split('\\n'):
        print(line)


# String String -> Integer
def get_last_hotfix_number_in_repo(repo, version_short_str):
    """
    Find the latest hotfix by looking at remote tag names
    """
    chdir_repo(repo)
    filter_tag_cmd = "awk '{ print $2 }'"
    filter_hotfix_number = "awk -F'.' '{ print $3 }'"

    tag = "{}{}".format(BRANCH_BASE, version_short_str)
    git_cmd = "git ls-remote origin 'refs/tags/{}.*'".format(tag)
    get_hotfix_cmd = "{} | {} | {}".format(git_cmd,
                                           filter_tag_cmd,
                                           filter_hotfix_number)
    result = subprocess.check_output(get_hotfix_cmd, shell=True)
    hotfixes = list(map(int, filter(lambda x: x.isdigit(),
                                    result.split(b'\n'))))
    hotfixes.sort()
    chdir_base()

    return hotfixes[-1]


# String String -> None
def checkout_ref(repo, ref):
    print("checking out {} ref for {} repo".format(ref, repo))
    chdir_repo(repo)
    subprocess.call('git fetch --tags -f', shell=True)
    subprocess.call('git checkout {}'.format(ref), shell=True)
    chdir_base()


def assert_packages():
    try:
        pkg_resources.require(get_dependencies())
    except VersionConflict as e:
        print("Missing a library requirement, please update:")
        print(str(e))
        sys.exit(0)


# None -> [List-of String]
def get_dependencies():
    with open("requirements.txt", 'r') as f:
        return f.read().split("\n")
