#!/bin/python
import subprocess, os, re, sys
import utils as util

from version import Version
from user_interaction import prompt_until_answer


repos = ['javarosa', 'commcare', 'commcare-odk']

# String String -> None
def create_branches_and_update_versions(branch_base, version):
    if util.unstaged_changes_present(repos):
        raise Exception("one of the branches has unstaged changes, please stash and try again")
    util.pull_masters()

    branch_name = "{}{}".format(branch_base, version)
    if util.branch_exists_in_repos(branch_name, repos):
        raise Exception("commcare_{} branch already exists".format(version))

    create_release_branches(branch_name)
    update_version_numbers()
    mark_version_as_alpha(branch_name)

# String -> None
def create_release_branches(branch_name):
    for repo in repos:
        util.chdir_repo(repo)
        subprocess.call('git checkout master', shell=True)
        subprocess.call('git checkout -b {}'.format(branch_name), shell=True)
        subprocess.call('git push origin {}'.format(branch_name), shell=True)
        subprocess.call('git checkout master', shell=True)
        util.chdir_base()

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
    util.chdir_repo('commcare')
    subprocess.call('git checkout master', shell=True)

    replace_func(replace_build_prop,
            'application/build.properties')
    replace_func(replace_config_engine_version,
            'util/src/org/commcare/util/CommCareConfigEngine.java')

    review_and_commit_changes('master',
            'Automated version bump')
    util.chdir_base()

# String String -> None
def review_and_commit_changes(branch, commit_msg):
    diff = subprocess.check_output("git diff", shell=True)
    util.print_with_newlines(str(diff))

    if prompt_until_answer('Proceed by pushing diff to {}?'.format(branch), True):
        subprocess.call('git add -u', shell=True)
        subprocess.call("git commit -m '{}'".format(commit_msg),
                shell=True)
        subprocess.call("git push origin {}".format(branch), shell=True)
    else:
        print("Exiting during code level version updates due to incorrect diff. You'll need to manually complete the deploy.")
        sys.exit(0)

# (String -> String) String -> None
def replace_func(func, file_name):
    tmp_file_name = '{}.new'.format(file_name)
    read_file = open(file_name, 'r', encoding='utf-8')
    write_file = open(tmp_file_name, 'w', encoding='utf-8', newline='\n')

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

    print('commcare build.properties: replacing {} with {}'.format(next_version, next_version.get_next_minor_release()))
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
    util.chdir_repo('commcare-odk')
    subprocess.call('git checkout master', shell=True)

    replace_func(update_manifest_version, 'app/AndroidManifest.xml')
    update_resource_string_version()

    review_and_commit_changes('master', 'Automated version bump')

    util.chdir_base()

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
    write_file = open(tmp_file_name, 'w', encoding='utf-8', newline='\n')

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
    util.chdir_repo('commcare')

    subprocess.call('git pull origin {}'.format(branch_name), shell=True)
    subprocess.call('git checkout {}'.format(branch_name), shell=True)
    replace_func(set_dev_tag_to_alpha, 'application/build.properties')

    review_and_commit_changes(branch_name, 
            'Automated commit adding dev tag to commcare version')
    subprocess.call('git checkout master', shell=True)
    util.chdir_base()

# String -> String
def set_dev_tag_to_alpha(file_contents):
    existing_version_tag = 'commcare.version=v${app.version}dev'
    new_version_tag = 'commcare.version=v${app.version}alpha'

    if file_contents.find(existing_version_tag) == -1:
        raise Exception("unable to find dev version tag in build.properties")

    return file_contents.replace(existing_version_tag, new_version_tag)

# String Version -> String
def create_release_tags(branch_base, version):
    if util.unstaged_changes_present(repos):
        raise Exception("one of the branches has unstaged changes, please stash and try again")

    branch_name = "{}{}".format(branch_base, version.short_string())
    tag_name = "{}{}".format(branch_base, version)

    if not util.branch_exists_in_repos(branch_name, repos):
        raise Exception("{} branch doesn't exist".format(branch_name))

    mark_version_as_release(branch_name)
    add_hotfix_version_to_odk(branch_name, 0)
    create_tag_from_branch(branch_name, tag_name)

    return tag_name

# String -> None
def mark_version_as_release(branch_name):
    util.chdir_repo('commcare')
    print("marking commcare {} branch for release".format(branch_name))

    subprocess.call('git pull origin {}'.format(branch_name), shell=True)
    subprocess.call('git checkout {}'.format(branch_name), shell=True)

    replace_func(set_dev_tag_to_release, 'application/build.properties')
    review_and_commit_changes(branch_name, 'Automated commit removing alpha tag from commcare version')

    util.chdir_base()

# String -> String
def set_dev_tag_to_release(file_contents):
    existing_version_tag = 'commcare.version=v${app.version}alpha'
    new_version_tag = 'commcare.version=v${app.version}'

    if file_contents.find(existing_version_tag) == -1:
        raise Exception("unable to find alpha version tag in build.properties")

    return file_contents.replace(existing_version_tag, new_version_tag)

# String Integer -> None
def add_hotfix_version_to_odk(branch_name, hotfix_count):
    util.chdir_repo('commcare-odk')

    print("adding hotfix version to {} branch of commcare-odk".format(branch_name))

    subprocess.call('git pull origin {}'.format(branch_name), shell=True)
    subprocess.call('git checkout {}'.format(branch_name), shell=True)

    replace_func(set_hotfix_version_to_zero, 'app/AndroidManifest.xml')
    review_and_commit_changes(branch_name, 'Automated commit adding hotfix version to AndroidManifest.xml')

    util.chdir_base()

# String -> String
def set_hotfix_version_to_zero(file_contents):
    versionPattern = re.compile(r'android:versionName="(\d+).(\d+)"')
    result = versionPattern.search(file_contents)
    if result == None or len(result.groups()) != 2:
        raise Exception('AndroidManifest expected version number of format _.__')
    version = result.groups()
    major = int(version[0])
    minor = int(version[1])
    current_version = 'android:versionName="{}.{}'.format(major, minor)
    version_with_hotfix_entry = '{}.0'.format(current_version)
    return file_contents.replace(current_version, version_with_hotfix_entry)

# String String -> None
def create_tag_from_branch(branch_name, tag_name):
    print("creating release tags '{}' from branches called '{}'".format(tag_name, branch_name))
    for repo in repos:
        util.chdir_repo(repo)
        subprocess.call('git checkout {}'.format(branch_name), shell=True)
        subprocess.call('git pull origin {}'.format(branch_name), shell=True)
        subprocess.call('git tag {}'.format(tag_name), shell=True)
        subprocess.call('git push origin {}'.format(tag_name), shell=True)
        util.chdir_base()

# String -> None
def close_branches(branch_name):
    if not branch_exists_in_repos(branch_name):
        raise Exception("commcare_{} branch doesn't exists".format(version))
    print('removing local instances of the {} branch'.format(branch_name))
    print("You will also want to close the remote github branches")
    print("\t(this will be automated once the script has been working for a while.)")

    for repo in repos:
        util.chdir_repo(repo)
        print("removing {} branch of {} repo".format(branch_name, repo))
        subprocess.call('git checkout master', shell=True)
        subprocess.call('git branch -d {}'.format(branch_name), shell=True)
        util.chdir_base()

def schedule_hotfix_release(branch_base, version):
    branch_name = "{}{}".format(branch_base, version.short_string())
    tag_name = "{}{}".format(branch_name, version)
    create_tag_from_branch(branch_name, tag_name)
