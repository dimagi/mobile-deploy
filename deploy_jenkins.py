#!/bin/python
import jenkins
import re
import subprocess
import os

from version import Version
from user_interaction import verify_value_with_user
from deploy_config import JENKINS_USER, JENKINS_PASSWORD,\
    BUILD_SERVER_USER, BUILD_SERVER

j = jenkins.Jenkins('http://jenkins.dimagi.com',
                    JENKINS_USER,
                    JENKINS_PASSWORD)

job_roots = ['javarosa-core-library', 'commcare-mobile', 'commcare-odk']

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

    set_build_numbers(version)
    inc_minor_version('commcare-mobile')
    inc_minor_version('commcare-mobile-{}'.format(version.short_string()))

    return version.short_string()

# None -> Version
def get_next_release_version():
    """
    Reads the version number off of the 'commcare-mobile' job, which should be
    set to the next release.
    """
    xml = j.get_job_config('commcare-mobile')

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
    print("old git tag: {}".format(old_tag_name))

    xml = xml.replace(old_tag_name,
                      'refs/heads/commcare_{}'.format(new_version))

    j.create_job(new_release_job_name, xml)

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

# Version -> None
def set_build_numbers(new_version):
    """
    Update next build number for new release jobs by 1 and master jobs by 2000.
    """
    print("updating build numbers on jenkins jobs")
    update_release_build_number('commcare-mobile', new_version, 1)
    update_release_build_number('commcare-odk', new_version, 1)
    update_master_build_number('commcare-mobile', 2000)
    update_master_build_number('commcare-odk', 2000)

# String Version Integer -> None
def update_release_build_number(job_base, current_version, increment_by):
    old_job = '{}-{}'.format(job_base, current_version.get_last_version_short())
    current_build_number = j.get_job_info(old_job)['nextBuildNumber']

    new_job = '{}-{}'.format(job_base, current_version.short_string())

    next_build_number = int(current_build_number) + increment_by

    print('INFO:\t{} build #: {}'.format(old_job, current_build_number))
    print('\t\tsetting {} build # to {}'.format(new_job, next_build_number))

    create_next_build_number_file(next_build_number)
    upload_next_build_number(new_job, next_build_number)

    os.remove('nextBuildNumber')

# String Integer -> None
def update_master_build_number(job_name, increment_by):
    current_build_number = j.get_job_info(job_name)['nextBuildNumber']

    next_build_number = int(current_build_number) + increment_by

    print('INFO\tupdating {} build # from {} to {}'.format(job_name,
                                                           current_build_number,
                                                           next_build_number))

    create_next_build_number_file(next_build_number)
    upload_next_build_number(job_name, next_build_number)

    os.remove('nextBuildNumber')

def create_next_build_number_file(next_build_number):
    f = open('nextBuildNumber', 'w', encoding='utf-8', newline='\n')
    f.write('{}\n'.format(next_build_number))
    f.close()

def upload_next_build_number(job_name, next_build_number):
    try:
        build_path = '/var/lib/jenkins/jobs/{}/nextBuildNumber'.format(job_name)
        scp_command = 'scp nextBuildNumber {}@{}:{}'.format(BUILD_SERVER_USER,
                                                            BUILD_SERVER,
                                                            build_path)
        subprocess.call(scp_command, shell=True)
    except Exception:
        show_manual_next_build_message(job_name, next_build_number)
        return

    # make jenkins read the build number change from memory
    reload_job_into_jenkins_memory(job_name)

def show_manual_next_build_message(job_name, next_build_number):
    print('Failed setting nextBuildNumber for {}'.format(job_name))
    next_build_url = ("http://jenkins.dimagi.com/" +
                      "job/{}/nextbuildnumber/").format(job_name)
    print(("Please manually set {}'s nextBuildNumber " +
           "to {} at \n {}").format(job_name, next_build_number,
                                    next_build_url))


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
    print("Incrementing the minor version # on {} jenkins job".format(job_name))
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
    """
    Bump the commcare-mobile VERSION build parameter of a release job by a
    hotfix version.
    """
    job_name = "commcare-mobile-{}".format(version.short_string())
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
        make_release_job_use_tag(job_root, branch, tag, version)

# String String String Version -> None
def make_release_job_use_tag(base_job_name, branch, tag, version):
    job_name = '{}-{}'.format(base_job_name, version.short_string())

    print("update {} to build off tag {}".format(job_name, tag))

    xml = j.get_job_config(job_name)
    xml = xml.replace("refs/heads/{}".format(branch),
                      "refs/tags/{}".format(tag))

    j.reconfig_job(job_name, xml)

# Version String -> None
def build_release(version):
    j.build_job("javarosa-core-library-{}".format(version.short_string()))
    print(("Release builds have been triggered. " +
           "When they finish (~10 minutes) name them {} " +
           "and mark 'keep this build forever'").format(version))

# None -> Version
def get_staged_release_version():
    """
    Reads the version number off of the commcare-mobile job, and use
    it to find the latest release job commcare-mobile-X.XX, from
    which the hotfix version can be loaded.
    """
    master_xml = j.get_job_config('commcare-mobile')

    versionPattern = re.compile(r'VERSION=(\d+).(\d+).(\d+)')
    next_version_raw = versionPattern.search(master_xml).groups()
    if len(next_version_raw) != 3:
        raise Exception("Couldn't find next version to deploy")
    next_version = Version(*map(int, next_version_raw))

    last_version = next_version.get_last_version_short()
    staged_release_job = 'commcare-mobile-{}'.format(last_version)
    release_xml = j.get_job_config(staged_release_job)
    current_version_raw = versionPattern.search(release_xml).groups()
    if len(current_version_raw) != 3:
        raise Exception("Couldn't find next version to deploy")
    return Version(*map(int, current_version_raw))
