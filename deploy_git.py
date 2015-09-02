#!/bin/python
import subprocess, os, re

from version import Version
from user_interaction import prompt_until_answer
import deploy_config as conf

repos = ['javarosa', 'commcare', 'commcare-odk']

# String String -> None
def create_branches_and_update_versions(branch_base, version):
    if unstaged_changes_present():
        raise Exception("one of the branches has unstaged changes, please stash and try again")
    pull_masters()

    branch_name = "{}{}".format(branch_base, version)
    if branch_exists_in_repos(branch_name):
        raise Exception("commcare_{} branch already exists".format(version))

    create_release_branches(branch_name)
    update_version_numbers()
    mark_version_as_alpha(branch_name)

# None -> Boolean
def unstaged_changes_present():
    for repo in repos:
        chdir_repo(repo)
        if b'' != subprocess.check_output("git status -s | sed '/^??/d'", shell=True):
            return True
        chdir_base()
    return False

# None -> None
def pull_masters():
    for repo in repos:
        chdir_repo(repo)
        subprocess.call('git pull origin master', shell=True)
        chdir_base()

# String -> Boolean
def branch_exists_in_repos(branch_name):
    for x in [branch_exists(repo, branch_name) for repo in repos]:
        if x:
            return True
    return False

# String String -> Boolean
def branch_exists(child_directory, branch_name):
    chdir_repo(child_directory)
    try:
        subprocess.check_output('git show-ref ' + branch_name, shell=True)
        return True
    except subprocess.CalledProcessError:
        return False
    finally:
        chdir_base()

# String -> None
def create_release_branches(branch_name):
    for repo in repos:
        chdir_repo(repo)
        subprocess.call('git checkout master', shell=True)
        subprocess.call('git checkout -b {}'.format(branch_name), shell=True)
        subprocess.call('git push origin {}'.format(branch_name), shell=True)
        chdir_base()

# None -> None
def update_version_numbers():
    update_commcare_version_numbers()
    update_odk_version_numbers()

# None -> None
def update_commcare_version_numbers():
    """
    Update version numbers in build.properties and CommCareConfigEngin on
    master.
    """
    chdir_repo('commcare')
    subprocess.call('git checkout master', shell=True)

    replace_func(replace_build_prop,
            'application/build.properties')
    replace_func(replace_config_engine_version,
            'util/src/org/commcare/util/CommCareConfigEngine.java')

    review_and_commit_changes('master',
            'Automated version bump')
    chdir_base()

# String String -> None
def review_and_commit_changes(branch, commit_msg):
    diff = subprocess.check_output("git diff", shell=True)
    print(diff)

    if prompt_until_answer('Proceed by pushing diff to {}?: [Y/n]'.format(branch), true):
        subprocess.call('git add -u', shell=True)
        subprocess.call("git commit -m {}".format(commit_msg),
                shell=True)
        subprocess.call("git push origin {}".format(branch), shell=True)
    else:
        print("Exiting during code level version updates due to incorrect diff. You'll need to manually complete the deploy.")
        exit(0)

# (String -> String) String -> None
def replace_func(func, file_name):
    tmp_file_name = '{}.new'.format(file_name)
    read_file = open(file_name, 'r', encoding='utf-8')
    write_file = open(tmp_file_name, 'w', encoding='utf-8')

    file_contents = ''
    for line in read_file.readlines():
        file_contents += line
    read_file.close()

    file_contents = func(file_contents)

    write_file.write(file_contents)
    write_file.close()

    os.rename(tmp_file_name, file_name)

# String -> String
def replace_build_prop(file_contents):
    versionPattern = re.compile(r'app.version=(\d+).(\d+).(\d+)')
    result = versionPattern.search(file_contents)
    if result == None or len(result.groups()) != 3:
        raise Exception("Couldn't parse version in build.properties")

    version = result.groups()
    next_version_raw = list(map(int, version))
    next_version = Version(*next_version_raw)

    print('build.properties: replacing {} with {}'.format(next_version, next_version.get_next_minor_release()))
    return file_contents.replace('app.version={}'.format(next_version),
            'app.version={}'.format(next_version.get_next_minor_release()))


# String -> String
def replace_config_engine_version(file_contents):
    versionPattern = re.compile(r'CommCarePlatform\((\d+), (\d+)\)')
    result = versionPattern.search(file_contents)
    if result == None or len(result.groups()) != 2:
        raise Exception("Couldn't parse version in CommCareConfigEngine")
    version_raw = result.groups()
    major = int(version_raw[0])
    minor = int(version_raw[1])

    print('CommCareConfigEngine: replacing {} with {}'.format(
        'CommCarePlatform({}, {})'.format(major, minor),
        'CommCarePlatform({}, {})'.format(major, minor + 1)))

    return file_contents.replace('CommCarePlatform({}, {})'.format(major, minor), 'CommCarePlatform({}, {})'.format(major, minor + 1))

# None -> None
def update_odk_version_numbers():
    """
    Update version numbers in AndroidManifest and push master.
    """
    chdir_repo('commcare-odk')
    subprocess.call('git checkout master', shell=True)

    replace_func(update_manifest_version, 'app/AndroidManifest.xml')
    update_resource_string_version()

    review_and_commit_changes('master', 'Automated version bump')

    chdir_base()

# String -> String
def update_manifest_version(file_contents):
    versionPattern = re.compile(r'android:versionName="(\d+).(\d+)"')
    result = versionPattern.search(file_contents)
    if result == None or len(result.groups()) != 2:
        raise
    version = result.groups()
    major = int(version[0])
    minor = int(version[1])
    current_version = 'android:versionName="{}.{}"'.format(major, minor)
    next_version = 'android:versionName="{}.{}"'.format(major, minor + 1)
    return file_contents.replace(current_version, next_version)

# String -> None
def update_resource_string_version():
    """ Update version in strings.xml. requires special logic because the
    version numbers are on different lines: 
    <integer-array name="commcare_version">
        <item>2</item>
        <item>22</item>
    </integer-array>
    """
    file_name = 'app/res/values/strings.xml'
    tmp_file_name = '{}.new'.format(file_name)
    read_file = open(file_name, 'r', encoding='utf-8')
    write_file = open(tmp_file_name, 'w', encoding='utf-8')

    file_contents = ''

    on_version_line = -1
    for line in read_file.readlines():
        if on_version_line == 1:
            # minor version
            print(line)
            versionPattern = re.compile(r'<item>(\d+)<')
            result = versionPattern.search(file_contents)
            if result == None:
                raise Exception("couldn't parse version")
            version = int(versionPattern.search(file_contents).groups()[0])
            line = "<item>{}</item>\n".format(version + 1)
            on_version_line = -1
        elif on_version_line == 0:
            # major version
            on_version_line = 1
            print(line)
        if line.find("commcare_version") != -1:
            on_version_line = 0
            print(line)
        file_contents += line

    read_file.close()

    write_file.write(file_contents)
    write_file.close()

    os.rename(tmp_file_name, file_name)

# String -> None
def mark_version_as_alpha(branch_name):
    chdir_repo('commcare')
    subprocess.call('git checkout {}'.format(branch_name), shell=True)
    replace_func(set_dev_tag_to_alpha, 'application/build.properties')

    review_and_commit_changes(branch_name, 
            'Automated commit adding dev tag to commcare version')
    chdir_base()

# String -> String
def set_dev_tag_to_alpha(file_contents):
    existing_version_tag = 'commcare.version=v${app.version}dev'
    new_version_tag = 'commcare.version=v${app.version}alpha'

    if file_contents.find(existing_version_tag) == -1:
        raise Exception("unable to find dev version tag in build.properties")

    return file_contents.replace(existing_version_tag, new_version_tag)

# String Version -> String
def schedule_minor_release(branch_base, version):
    branch_name = "{}{}".format(branch_base, version.short_string())
    tag_name = "{}{}".format(branch_name, version)

    mark_version_as_release(branch_name)
    create_tag_from_branch(branch_name, tag_name)
    return tag_name

# String -> None
def mark_version_as_release(branch_name):
    chdir_repo('commcare')

    subprocess.call('git checkout {}'.format(branch_name), shell=True)

    replace_func(set_dev_tag_to_release, 'application/build.properties')
    review_and_commit_changes(branch_name, 'Automated commit removing alpha tag from commcare version')

    chdir_base()

# String -> String
def set_dev_tag_to_release(file_contents):
    existing_version_tag = 'commcare.version=v${app.version}alpha'
    new_version_tag = 'commcare.version=v${app.version}'

    if file_contents.find(existing_version_tag) == -1:
        raise Exception("unable to find alpha version tag in build.properties")

    return file_contents.replace(existing_version_tag, new_version_tag)

def create_tag_from_branch(branch_name, tag_name):
    for repo in repos:
        chdir_repo(repo)
        subprocess.call('git checkout -b {}'.format(branch_name), shell=True)
        subprocess.call('git pull', shell=True)
        subprocess.call('git tag {}'.format(tag_name), shell=True)
        subprocess.call('git push origin {}'.format(tag_name), shell=True)
        chdir_base()

def schedule_hotfix_release(branch_base, version):
    branch_name = "{}{}".format(branch_base, version.short_string())
    tag_name = "{}{}".format(branch_name, version)
    create_tag_from_branch(branch_name, tag_name)


# String -> None
def chdir_repo(repo):
    os.chdir(os.path.join(conf.BASE_DIR, repo))

# None -> None
def chdir_base():
    os.chdir(conf.BASE_DIR)
