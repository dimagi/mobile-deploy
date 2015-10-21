import subprocess
import os
from deploy_config import BASE_DIR, BRANCH_BASE


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
        command_result = subprocess.check_output("git status -s | sed '/^??/d'",
                                                 shell=True)
        if b'' != command_result:
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


# String Version -> Integer
def get_last_hotfix_number_in_repo(repo, version):
        chdir_repo(repo)
        filter_tag_cmd = "awk '{ print $2 }'"
        filter_hotfix_number = "awk -F'.' '{ print $3 }'"

        tag = "{}{}".format(BRANCH_BASE, version.short_string())
        git_cmd = "git ls-remote origin 'refs/tags/{}.*'".format(tag)
        get_hotfix_cmd = "{} | {} | {}".format(git_cmd,
                                               filter_tag_cmd,
                                               filter_hotfix_number)
        result = subprocess.check_output(get_hotfix_cmd, shell=True)
        hotfixes = list(map(int, filter(lambda x: x != b'',
                                        result.split(b'\n'))))
        hotfixes.sort()
        chdir_base()

        return hotfixes[-1]


# String String -> None
def checkout_ref(repo, ref):
    print("checking out {} ref for {} repo".format(ref, repo))
    chdir_repo(repo)
    subprocess.call('git pull --tags', shell=True)
    subprocess.call('git checkout {}'.format(ref), shell=True)
    chdir_base()
