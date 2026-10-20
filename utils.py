import subprocess
import os
import re
from deploy_config import BASE_DIR, BRANCH_BASE
import sys
from importlib import metadata


# None -> None
def pull_masters(repos):
    for repo in repos:
        chdir_repo(repo)
        subprocess.check_call(['git', 'checkout', 'master'])
        subprocess.check_call(['git', 'pull', '--ff-only', 'origin', 'master'])
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
        status = subprocess.check_output(['git', 'status', '-s'], text=True)
        chdir_base()
        if any(not line.startswith('??') for line in status.splitlines()):
            return True
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


# String String -> Integer
def get_last_hotfix_number_in_repo(repo, version_short_str):
    """
    Find the latest hotfix by looking at remote tag names
    """
    chdir_repo(repo)
    tag = "{}{}".format(BRANCH_BASE, version_short_str)
    result = subprocess.check_output(
        ['git', 'ls-remote', 'origin', 'refs/tags/{}.*'.format(tag)],
        text=True)
    hotfixes = []
    for line in result.splitlines():
        hotfix = line.split()[-1].split('.')[-1]
        if hotfix.isdigit():
            hotfixes.append(int(hotfix))
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
    for name, operator, required in get_dependencies():
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        if installed is None or not version_satisfies(installed, operator,
                                                      required):
            print("Missing a library requirement, please update:")
            print("{}{}{} required, found {}".format(name, operator,
                                                     required, installed))
            sys.exit(0)


# String String String -> Boolean
def version_satisfies(installed, operator, required):
    def as_tuple(v):
        return tuple(int(part) for part in re.findall(r'\d+', v)[:3])
    if operator == '==':
        return as_tuple(installed) == as_tuple(required)
    return as_tuple(installed) < as_tuple(required)


# None -> [List-of (String, String, String)]
def get_dependencies():
    with open("requirements.txt", 'r') as f:
        lines = [line.strip() for line in f.read().splitlines()]
    return [re.match(r'([\w.\-]+)\s*(==|<)\s*(\S+)', line).groups()
            for line in lines if line]
