#!/bin/python
import jenkins
import re
import subprocess
import os
import xml.etree.ElementTree as ET

import utils as util

from version import Version
from user_interaction import verify_value_with_user
from deploy_config import JENKINS_USER, JENKINS_PASSWORD,\
    BUILD_SERVER_USER, BUILD_SERVER, BRANCH_BASE

MOBILE_VIEW_NAME = "CommCare Mobile"
ARCHIVED_MOBILE_VIEW_NAME = "CommCare Mobile Archive"

j = jenkins.Jenkins('https://jenkins.dimagi.com',
                    JENKINS_USER,
                    JENKINS_PASSWORD)

job_roots = ['commcare-core', 'commcare-android']
repo_to_jobs = {'commcare-core': 'commcare-core',
                'commcare-android': 'commcare-android'}


# None -> String
def create_new_release_jobs():
    """
    Copy last releases jenkins jobs and update values to mirror the release
    being staged.
    """
    version = get_next_release_version()

    last_release = version.get_last_version_short()

    verify_message = ("Are these values correct?: " +
                      "last release: {}, this release {}").format(last_release,
                                                                  version)
    exit_message = "Release versions from jenkins are incorrect, exiting."
    verify_value_with_user(verify_message, exit_message)

    assert_jobs_dont_exist(version)

    for job_root in job_roots:
        create_new_release_job(job_root, last_release, version)
        archive_old_release_job(job_root, version)

    set_build_numbers(version)
    inc_minor_version('commcare-core')
    inc_minor_version('commcare-core-{}'.format(version.short_string()))

    return version.short_string()


# None -> Version
def get_next_release_version():
    """
    Reads the version number off of the 'commcare-core' job, which should be
    set to the next release.
    """
    xml = j.get_job_config('commcare-android')

    versionPattern = re.compile(r'VERSION=(\d+).(\d+).(\d+)')
    current_version_raw = versionPattern.search(xml).groups()
    if len(current_version_raw) != 3:
        raise Exception("Couldn't find next version to deploy")
    return Version(*map(int, current_version_raw))


# Version -> None
def assert_jobs_dont_exist(version):
    for job_root in job_roots:
        job = '{}-{}'.format(job_root, version.short_string())
        if j.job_exists(job):
            raise Exception("'{}' jenkins job already exists".format(job))


# String String Version -> None
def create_new_release_job(base_job_name, last_release, new_release_version):
    last_release_job_name = '{}-{}'.format(base_job_name, last_release)
    xml = j.get_job_config(last_release_job_name)

    new_version = new_release_version.short_string()
    new_release_job_name = '{}-{}'.format(base_job_name, new_version)

    print("Creating job '{}' from old job '{}'".format(new_release_job_name,
                                                       last_release_job_name))

    xml = replace_references_to_old_jobs(xml, last_release, new_version)

    old_tag_name = get_old_git_tag(xml)
    new_ref_name = 'refs/heads/commcare_{}'.format(new_version)
    print("Replacing git tag from {} to {}".format(old_tag_name, new_ref_name))

    xml = xml.replace(old_tag_name, new_ref_name)

    j.create_job(new_release_job_name, xml)
    print("Adding {} job to {} view".format(new_release_job_name,
                                            MOBILE_VIEW_NAME))
    add_job_to_view(new_release_job_name, MOBILE_VIEW_NAME)


def replace_references_to_old_jobs(xml, last_release, new_version):
    for job_base in job_roots:
        xml = xml.replace('{}-{}'.format(job_base, last_release),
                          '{}-{}'.format(job_base, new_version))
    return xml


def get_old_git_tag(xml):
    versionPattern = re.compile(r'refs/tags/commcare_(\d+).(\d+).(\d+)')
    branch_version_numbers = versionPattern.search(xml).groups()

    if len(branch_version_numbers) != 3:
        raise Exception("couldn't find git branch reference of format " +
                        "refs/tags/commcare_X.X.X")

    return 'refs/tags/commcare_{}.{}.{}'.format(*branch_version_numbers)


# String Version -> None
def archive_old_release_job(base_job_name, version):
    two_release_ago = Version(version.major, version.minor - 2, 0)
    last_release_job_name = '{}-{}'.format(base_job_name,
                                           two_release_ago.short_string())

    print("moving {} to {} view".format(last_release_job_name,
                                        ARCHIVED_MOBILE_VIEW_NAME))

    remove_job_from_view(last_release_job_name, MOBILE_VIEW_NAME)
    add_job_to_view(last_release_job_name, ARCHIVED_MOBILE_VIEW_NAME)


# String -> None
def add_job_to_view(job_name, view_name):
    xml = j.get_view_config(view_name)
    tree = ET.fromstring(xml)
    jobs = tree.find('jobNames')
    e = ET.SubElement(jobs, 'string')
    e.text = job_name

    new_xml = ET.tostring(tree).decode('utf-8')
    j.reconfig_view(view_name, new_xml)


# String -> None
def remove_job_from_view(job_name, view_name):
    xml = j.get_view_config(view_name)
    tree = ET.fromstring(xml)
    jobs = tree.find('jobNames')
    for job in jobs.getchildren():
        if job.text == job_name:
            jobs.remove(job)
            break

    new_xml = ET.tostring(tree).decode('utf-8')
    j.reconfig_view(view_name, new_xml)


# Version -> None
def set_build_numbers(new_version):
    """
    Update next build number for new release jobs by 1 and master jobs by 2000.
    """
    print("updating build numbers on jenkins jobs")
    update_release_build_number('commcare-core', new_version, 1)
    update_release_build_number('commcare-android', new_version, 1)
    update_master_build_number('commcare-core', 2000)
    update_master_build_number('commcare-android', 2000)


# String Version Integer -> None
def update_release_build_number(job_base, current_version, increment_by):
    current_build_number = j.get_job_info(job_base)['nextBuildNumber']

    new_job = '{}-{}'.format(job_base, current_version.short_string())

    next_build_number = int(current_build_number) + increment_by

    print('INFO:\t{} build #: {}'.format(job_base, current_build_number))
    print('\t\tsetting {} build # to {}'.format(new_job, next_build_number))

    create_next_build_number_file(next_build_number)
    upload_next_build_number(new_job, next_build_number)

    os.remove('nextBuildNumber')


# String Integer -> None
def update_master_build_number(job_name, increment_by):
    current_build_number = j.get_job_info(job_name)['nextBuildNumber']

    next_build_number = int(current_build_number) + increment_by

    print("INFO\tupdating {} build # " +
          "from {} to {}".format(job_name,
                                 current_build_number,
                                 next_build_number))

    create_next_build_number_file(next_build_number)
    upload_next_build_number(job_name, next_build_number)

    os.remove('nextBuildNumber')


def create_next_build_number_file(next_build_number):
    f = open('nextBuildNumber', 'w', encoding='utf-8', newline='\n')
    f.write('{}\n'.format(next_build_number))
    f.close()


# String Integer -> None
def upload_next_build_number(job, next_build_number):
    try:
        build_path = '/var/lib/jenkins/jobs/{}/nextBuildNumber'.format(job)
        scp_command = 'scp nextBuildNumber {}@{}:{}'.format(BUILD_SERVER_USER,
                                                            BUILD_SERVER,
                                                            build_path)
        scp_successful = subprocess.call(scp_command, shell=True)
    except Exception:
        show_manual_next_build_message(job, next_build_number)
        return

    if scp_successful == 0:
        # make jenkins read the build number change from memory
        reload_job_into_jenkins_memory(job)
    else:
        show_manual_next_build_message(job, next_build_number)


# String Integer -> None
def show_manual_next_build_message(job_name, next_build_number):
    print('Failed setting nextBuildNumber for {}'.format(job_name))
    next_build_url = ("https://jenkins.dimagi.com/" +
                      "job/{}/nextbuildnumber/").format(job_name)
    print(("Please manually set {}'s nextBuildNumber " +
           "to {} at \n {}").format(job_name, next_build_number,
                                    next_build_url))


# String -> None
def reload_job_into_jenkins_memory(job_name):
    """
    Force jenkins to reload a job config from memory. Necessary if config
    files, such as nextBuildNumber, have changed.
    """
    xml = j.get_job_config(job_name)
    j.reconfig_job(job_name, xml)


# String -> None
def inc_minor_version(job_name):
    """
    Bump the VERSION build parameter by a minor version.
    """
    print(("Incrementing the minor version # on " +
           "{} jenkins job").format(job_name))
    xml = j.get_job_config(job_name)
    versionPattern = re.compile(r'VERSION=(\d+).(\d+).(\d+)')
    current_version_raw = versionPattern.search(xml).groups()

    if len(current_version_raw) != 3:
        raise Exception("Couldn't parse version")
    current_version = Version(*map(int, current_version_raw))
    next_minor_version = current_version.get_next_minor_release()

    print('changing {} version reference {} to {}'.format(job_name,
                                                          current_version,
                                                          next_minor_version))

    xml = xml.replace("VERSION={}".format(current_version),
                      "VERSION={}".format(next_minor_version))

    j.reconfig_job(job_name, xml)


# String -> None
def inc_hotfix_version(version):
    inc_hotfix_version_on_job("commcare-android", version)


# String String -> None
def inc_hotfix_version_on_job(base_job_name, version):
    """
    Bump the commcare-android VERSION build parameter of a release job by a
    hotfix version.
    """
    job_name = "{}-{}".format(base_job_name, version.short_string())
    xml = j.get_job_config(job_name)
    versionPattern = re.compile(r'VERSION=(\d+).(\d+).(\d+)')
    current_version_raw = versionPattern.search(xml).groups()

    if len(current_version_raw) != 3:
        raise Exception("Couldn't parse version")
    current_version = Version(*map(int, current_version_raw))
    next_hotfix_version = current_version.get_next_hotfix()

    print('changing {} version reference {} to {}'.format(job_name,
                                                          current_version,
                                                          next_hotfix_version))

    xml = xml.replace("VERSION={}".format(current_version),
                      "VERSION={}".format(next_hotfix_version))

    j.reconfig_job(job_name, xml)


def update_job_with_hotfix(current_version):
    return


# String String Version -> None
def make_release_jobs_use_tags(branch, tag, version):
    for job_root in job_roots:
        make_release_job_use_tag(job_root, version, branch, tag,
                                 job_root == "commcare-android")


# String String String String Boolean -> None
def make_release_job_use_tag(base_job_name, version_str, branch, tag,
                             update_core_ref):
    full_branch = "refs/heads/{}".format(branch)
    full_tag = "refs/tags/{}".format(tag)

    replacement_map = [(full_branch, full_tag)]

    if update_core_ref:
        # commcare-android-X.XX uses CCCORE_BRANCH to checkout the proper
        # commcare-core branch
        full_core_branch = "CCCORE_BRANCH={}".format(branch)
        full_core_tag = "CCCORE_BRANCH={}".format(tag)
        replacement_map.append((full_core_branch, full_core_tag))

    replace_references_in_job(base_job_name, version_str,
                              replacement_map)


# String String String String Boolean -> None
def make_release_job_use_branch(base_job_name, version_str, tag, branch,
                                update_core_ref):
    full_tag = "refs/tags/{}".format(tag)
    full_branch = "refs/heads/{}".format(branch)

    replacement_map = [(full_tag, full_branch)]

    if update_core_ref:
        # commcare-android-X.XX uses CCCORE_BRANCH to checkout the proper
        # commcare-core branch
        full_core_tag = "CCCORE_BRANCH={}".format(tag)
        full_core_branch = "CCCORE_BRANCH={}".format(branch)
        replacement_map.append((full_core_tag, full_core_branch))

    print(("changing jenkins job {} to build with following update" +
           "{}").format(base_job_name, replacement_map))

    replace_references_in_job(base_job_name, version_str,
                              replacement_map)


# String String [List-of (String, String)] -> None
def replace_references_in_job(base_job_name, version_str, replacement_map):
    job_name = '{}-{}'.format(base_job_name, version_str)

    print("updating {} to build with: {}".format(job_name, replacement_map))

    xml = j.get_job_config(job_name)
    for current_ref, new_ref in replacement_map:
        xml = xml.replace(current_ref, new_ref)

    j.reconfig_job(job_name, xml)


# Version String -> None
def build_release(version):
    j.build_job("commcare-core-{}".format(version.short_string()))
    print(("Release builds have been triggered. " +
           "When they finish (~10 minutes) name them {} " +
           "and mark 'keep this build forever'").format(version))


# None -> Version
def get_latest_release_job_version():
    """
    Reads the version number off of the commcare-android job, and use it to
    find the hotfix version in the latest commcare-android-X.XX job.
    """
    master_xml = j.get_job_config('commcare-android')

    versionPattern = re.compile(r'VERSION=(\d+).(\d+).(\d+)')
    next_version_raw = versionPattern.search(master_xml).groups()
    if len(next_version_raw) != 3:
        raise Exception("Couldn't find next version to deploy")
    next_version = Version(*map(int, next_version_raw))

    last_version = next_version.get_last_version_short()
    staged_release_job = 'commcare-android-{}'.format(last_version)
    release_xml = j.get_job_config(staged_release_job)
    current_version_raw = versionPattern.search(release_xml).groups()
    if len(current_version_raw) != 3:
        raise Exception("Couldn't find next version to deploy")
    return Version(*map(int, current_version_raw))


# [List-of String] -> None
def build_jobs_against_hotfix_branches(hotfix_repos):
    """
    Make release jobs for hotfix repos build off of the newly opened hotfix
    branches.
    """
    # NOTE PLM: not sure if the hotfix version is correct, but it is okay
    # because it isn't used here
    version = get_latest_release_job_version()
    version_short = version.short_string()

    for repo in hotfix_repos:
        last_hotfix = util.get_last_hotfix_number_in_repo(repo, version_short)
        hotfix_version = Version(version.major,
                                 version.minor,
                                 last_hotfix)
        tag = get_tag_name(hotfix_version)
        job_name = repo_to_jobs[repo]
        branch = get_branch_name(version)
        update_core_ref = (repo == "commcare-android" and
                           "commcare-core" in hotfix_repos)
        make_release_job_use_branch(job_name, version.short_string(),
                                    tag, branch, update_core_ref)


# [List-of String] -> None
def build_jobs_against_hotfix_tags(hotfix_repos):
    """
    Make release jobs for hotfix repos build off of the newly created hotfix
    tags.
    """
    # NOTE PLM: not sure if the hotfix version is correct, but it is okay
    # because it isn't used here
    version = get_latest_release_job_version()
    version_short = version.short_string()

    for repo in hotfix_repos:
        last_hotfix = util.get_last_hotfix_number_in_repo(repo, version_short)
        hotfix_version = Version(version.major,
                                 version.minor,
                                 last_hotfix)
        tag = get_tag_name(hotfix_version)
        job_name = repo_to_jobs[repo]
        branch = get_branch_name(version)
        update_core_ref = (repo == "commcare-android" and
                           "commcare-core" in hotfix_repos)
        make_release_job_use_tag(job_name, version.short_string(), branch, tag,
                                 update_core_ref)


def get_branch_name(v):
    return "{}{}".format(BRANCH_BASE, v.short_string())


def get_tag_name(v):
    return "{}{}".format(BRANCH_BASE, v)
