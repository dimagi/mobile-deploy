import subprocess
import os
import deploy_config as conf

# None -> None
def pull_masters(repos):
    for repo in repos:
        chdir_repo(repo)
        subprocess.call('git pull origin master', shell=True)
        chdir_base()


# String -> None
def chdir_repo(repo):
    os.chdir(os.path.join(conf.BASE_DIR, repo))


# None -> None
def chdir_base():
    os.chdir(conf.BASE_DIR)


# None -> Boolean
def unstaged_changes_present(repos):
    for repo in repos:
        chdir_repo(repo)
        if b'' != subprocess.check_output("git status -s | sed '/^??/d'", shell=True):
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
        result = subprocess.check_output('git show-ref {}'.format(branch_name), shell=True)
        return str(result).find('remotes/origin/{}'.format(branch_name)) != -1
    except subprocess.CalledProcessError:
        return False
    finally:
        chdir_base()


# String -> None
def print_with_newlines(msg):
    for line in msg.split('\\n'):
        print(line)
