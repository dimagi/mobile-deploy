#!/bin/python

import subprocess
import os
import re
import sys
import utils as util

import jenkins_utils

from version import Version
from user_interaction import prompt_until_answer
from deploy_config import REPOS, BRANCH_BASE


# String String -> None
def create_branches_and_update_versions(branch_base, version):
    if util.unstaged_changes_present(REPOS):
        raise Exception("one of the branches has unstaged changes, " +
                        "please stash and try again")
    util.pull_masters(REPOS)

    branch_name = "{}{}".format(branch_base, version)
    if util.branch_exists_in_repos(branch_name, REPOS):
        raise Exception("commcare_{} branch already exists".format(version))

    create_release_branches(branch_name)
    update_version_numbers()
    # enable for J2ME build
    # mark_version_as_alpha(branch_name)


# String -> None
def create_release_branches(branch_name):
    for repo in REPOS:
        checkout_master(repo)
        create_branch(repo, branch_name)
        checkout_master(repo)


# String -> None
def checkout_master(repo):
        util.chdir_repo(repo)
        subprocess.call('git checkout master', shell=True)
        util.chdir_base()


# String String -> None
def create_branch(repo, branch_name):
        util.chdir_repo(repo)
        subprocess.call('git checkout -b {}'.format(branch_name), shell=True)
        subprocess.call('git push origin {}'.format(branch_name), shell=True)
        util.chdir_base()


# None -> None
def update_version_numbers():
    update_commcare_version_numbers()
    update_android_version_numbers()


# None -> None
def update_commcare_version_numbers():
    """
    Update version numbers in build.properties and CommCareConfigEngin on
    master.
    """
    util.chdir_repo('commcare-core')
    subprocess.call('git checkout master', shell=True)

    replace_func(replace_config_engine_version,
                 'src/cli/java/org/commcare/util/engine/CommCareConfigEngine.java')

    review_and_commit_changes('master',
                              'Automated version bump')
    util.chdir_base()


# String -> None
def update_commcare_hotfix_version_numbers(branch):
    """
    Update hotfix version in build.properties on hotfix branch
    """
    util.chdir_repo('commcare-core')
    subprocess.call('git checkout {}'.format(branch), shell=True)

    replace_func(incr_build_prop_hotfix_version,
                 'application/build.properties')

    review_and_commit_changes(branch,
                              'Automated hotfix version bump')
    util.chdir_base()


# String String -> None
def review_and_commit_changes(branch, commit_msg):
    diff = subprocess.check_output("git diff", shell=True)
    util.print_with_newlines(str(diff))

    question = 'Proceed by pushing diff to {}?'.format(branch)
    if prompt_until_answer(question, True):
        subprocess.call('git add -u', shell=True)
        subprocess.call("git commit -m '{}'".format(commit_msg),
                        shell=True)
        subprocess.call("git push origin {}".format(branch), shell=True)
    else:
        print("Exiting during code level version updates due to " +
              "incorrect diff. You'll need to manually complete the deploy.")
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
def incr_build_prop_minor_version(file_contents):
    return replace_build_prop(file_contents,
                              lambda v: v.get_next_minor_release())


# String -> String
def incr_build_prop_hotfix_version(file_contents):
    return replace_build_prop(file_contents,
                              lambda v: v.get_next_hotfix())


# String [Version -> Version] -> String
def replace_build_prop(file_contents, get_new_version):
    versionPattern = re.compile(r'app.version=(\d+).(\d+).(\d+)')
    result = versionPattern.search(file_contents)
    if result is None or len(result.groups()) != 3:
        raise Exception("Couldn't parse version in build.properties")

    version_raw = list(map(int, result.groups()))
    version = Version(*version_raw)

    next_minor = get_new_version(version)
    print('commcare build.properties: replacing {} with {}'.format(version,
                                                                   next_minor))
    return file_contents.replace('app.version={}'.format(version),
                                 'app.version={}'.format(next_minor))


# String -> String
def replace_config_engine_version(file_contents):
    majorVersionPattern = re.compile(r'MAJOR_VERSION = (\d+);')
    minorVersionPattern = re.compile(r'MINOR_VERSION = (\d+);')
    majorResult = majorVersionPattern.search(file_contents)
    minorResult = minorVersionPattern.search(file_contents)
    if minorResult is None or majorResult is None:
        raise Exception("Couldn't parse version in CommCareConfigEngine")
    major = int(majorResult.groups()[0])
    minor = int(minorResult.groups()[0])

    platform_pattern = 'CommCarePlatform({}, {})'.format(major, minor)
    new_platform = 'CommCarePlatform({}, {})'.format(major, minor + 1)
    print('CommCareConfigEngine: replacing {} with {}'.format(platform_pattern,
                                                              new_platform))

    return file_contents.replace(platform_pattern, new_platform)


# None -> None
def update_android_version_numbers():
    """
    Update version numbers in AndroidManifest and push master.
    """
    util.chdir_repo('commcare-android')
    subprocess.call('git checkout master', shell=True)

    replace_func(update_manifest_version, 'app/AndroidManifest.xml')

    review_and_commit_changes('master', 'Automated version bump')

    util.chdir_base()


# String -> String
def update_manifest_version(file_contents):
    versionPattern = re.compile(r'android:versionName="(\d+).(\d+)"')
    result = versionPattern.search(file_contents)
    if result is None or len(result.groups()) != 2:
        raise
    version = result.groups()
    major = int(version[0])
    minor = int(version[1])
    current_version = 'android:versionName="{}.{}"'.format(major, minor)
    next_version = 'android:versionName="{}.{}"'.format(major, minor + 1)
    return file_contents.replace(current_version, next_version)

# String -> None
def mark_version_as_alpha(branch_name):
    util.chdir_repo('commcare-core')

    subprocess.call('git checkout {}'.format(branch_name), shell=True)
    subprocess.call('git pull origin {}'.format(branch_name), shell=True)
    replace_func(set_dev_tag_to_alpha, 'application/build.properties')
    commit_message = 'Automated commit adding dev tag to commcare version'
    review_and_commit_changes(branch_name, commit_message)
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
    if util.unstaged_changes_present(REPOS):
        raise Exception("A branch has unstaged changes, stash and try again")

    branch_name = "{}{}".format(branch_base, version.short_string())
    tag_name = "{}{}".format(branch_base, version)

    if not util.branch_exists_in_repos(branch_name, REPOS):
        raise Exception("{} branch doesn't exist".format(branch_name))

    # TODO PLM: run this on J2ME releases:
    # mark_version_as_release(branch_name)
    add_hotfix_version_to_android(branch_name, 0)
    create_tags_for_repos(branch_name, tag_name)

    return tag_name


# String -> None
def mark_version_as_release(branch_name):
    util.chdir_repo('commcare-j2me')
    print("marking commcare-core {} branch for release".format(branch_name))

    subprocess.call('git checkout {}'.format(branch_name), shell=True)
    subprocess.call('git pull origin {}'.format(branch_name), shell=True)

    replace_func(set_dev_tag_to_release, 'application/build.properties')
    commit_message = "Automated: removing 'alpha' from version"
    review_and_commit_changes(branch_name, commit_message)

    util.chdir_base()


# String -> String
def set_dev_tag_to_release(file_contents):
    existing_version_tag = 'commcare.version=v${app.version}alpha'
    new_version_tag = 'commcare.version=v${app.version}'

    if file_contents.find(existing_version_tag) == -1:
        raise Exception("unable to find alpha version tag in build.properties")

    return file_contents.replace(existing_version_tag, new_version_tag)


# String Integer -> None
def add_hotfix_version_to_android(branch_name, hotfix_count):
    util.chdir_repo('commcare-android')

    print("add hotfix ver. to commcare-android branch {}".format(branch_name))

    subprocess.call('git checkout {}'.format(branch_name), shell=True)
    subprocess.call('git pull origin {}'.format(branch_name), shell=True)

    replace_func(set_hotfix_version_to_zero, 'app/AndroidManifest.xml')
    commit_message = 'Automated: adding hotfix version to AndroidManifest'
    review_and_commit_changes(branch_name, commit_message)

    util.chdir_base()


# String -> String
def set_hotfix_version_to_zero(file_contents):
    versionPattern = re.compile(r'android:versionName="(\d+).(\d+)"')
    result = versionPattern.search(file_contents)
    if result is None or len(result.groups()) != 2:
        raise Exception('Expected AndroidManifest version number format _.__, got {!s}'.format(result))
    version = result.groups()
    major = int(version[0])
    minor = int(version[1])
    current_version = 'android:versionName="{}.{}'.format(major, minor)
    version_with_hotfix_entry = '{}.0'.format(current_version)
    return file_contents.replace(current_version, version_with_hotfix_entry)


# String String -> None
def create_tags_for_repos(branch_name, tag_name):
    """
    Creates the release tag from provided branch.
    """
    print("creating release tags '{}' from '{}' branches".format(tag_name,
                                                                 branch_name))
    for repo in REPOS:
        util.chdir_repo(repo)
        create_tag_from_branch(branch_name, tag_name)
        util.chdir_base()


# String String -> None
def create_tag_from_branch(branch_name, tag_name):
    subprocess.call('git checkout {}'.format(branch_name), shell=True)
    subprocess.call('git pull origin {}'.format(branch_name), shell=True)
    subprocess.call('git tag {}'.format(tag_name), shell=True)
    subprocess.call('git push origin {}'.format(tag_name), shell=True)


# String -> None
def close_branches(branch_name):
    if not util.branch_exists_in_repos(branch_name, REPOS):
        raise Exception("{} branch doesn't exists".format(branch_name))
    print("removing local instances of the {} branch".format(branch_name))
    print("You will also want to close the remote github branches")
    print("\tthis'll be automated once the script's been working for a while.")

    for repo in REPOS:
        util.chdir_repo(repo)
        print("removing {} branch of {} repo".format(branch_name, repo))
        subprocess.call('git checkout master', shell=True)
        subprocess.call('git branch -d {}'.format(branch_name), shell=True)
        util.chdir_base()


# [List-of String] String Version -> None
def create_hotfix_tags(hotfix_repos, version):
    """
    Create hotfix tags from hotfix branch for given repos.
    """
    branch_name = "{}{}".format(BRANCH_BASE, version.short_string())
    tag_name = "{}{}".format(BRANCH_BASE, version)

    for repo in hotfix_repos:
        util.chdir_repo(repo)
        create_tag_from_branch(branch_name, tag_name)
        util.chdir_base()


# Version -> None
def checkout_latest_hotfix_tags(version):
    for repo in REPOS:
        checkout_latest_hotfix_tag(version, repo)


def checkout_latest_hotfix_tag(version, repo):
    def get_tag_name(v): return "{}{}".format(BRANCH_BASE, v)

    hotfix_version = get_last_hotfix(repo, version)
    tag = get_tag_name(hotfix_version)
    util.checkout_ref(repo, tag)


# String Version -> Version
def get_last_hotfix(repo, version):
    hotfix_number = util.get_last_hotfix_number_in_repo(repo,
                                                        version.short_string())
    return Version(version.major, version.minor, hotfix_number)


# Version [List-of String] -> None
def create_hotfix_branches(version, repos_to_hotfix):
    def get_branch_name(v): return "{}{}".format(BRANCH_BASE, v.short_string())

    branch = get_branch_name(version)
    for repo in repos_to_hotfix:
        print(("creating hotfix branch {} for " +
               "{} repo from latest tag").format(branch, repo))
        create_branch(repo, branch)

    # NOTE: needed for J2ME builds
    # if "commcare-core" in repos_to_hotfix:
    #   update_commcare_hotfix_version_numbers(branch)

    update_android_hotfix_version(branch)


# String -> None
def update_android_hotfix_version(branch):
    """
    Update hotfix version in AndroidManifest and push hotfix branch.
    """
    util.chdir_repo('commcare-android')
    subprocess.call('git checkout {}'.format(branch), shell=True)

    replace_func(update_manifest_hotfix_version, 'app/AndroidManifest.xml')

    review_and_commit_changes(branch, 'Automated hotfix version bump')

    util.chdir_base()


# String -> String
def update_manifest_hotfix_version(file_contents):
    versionPattern = re.compile(r'android:versionName="(\d+).(\d+).(\d+)"')
    result = versionPattern.search(file_contents)
    if result is None or len(result.groups()) != 3:
        raise
    version_raw = list(map(int, result.groups()))
    version = Version(*version_raw)
    current_version = 'android:versionName="{}"'.format(version)
    next_version = 'android:versionName="{}"'.format(version.get_next_hotfix())
    return file_contents.replace(current_version, next_version)


# None -> Version
def get_current_hotfix_version_from_release_tags():
    v = jenkins_utils.get_current_release_version()
    last_hotfix = -1
    for repo in ["commcare-core", "commcare-android"]:
        repo_hotfix = util.get_last_hotfix_number_in_repo(repo,
                                                          v.short_string())
        last_hotfix = max(last_hotfix, repo_hotfix)
    return Version(v.major, v.minor, last_hotfix)


# None -> Version
def get_next_hotfix_version_from_release_tags():
    return get_current_hotfix_version_from_release_tags().get_next_hotfix()


def close_hotfix_branches():
    # TODO
    return
