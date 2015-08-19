#!/bin/python
import jenkins, re
import subprocess, os

from version import Version

USER = ''
PASSWORD = ''

if USER == '' or PASSWORD == '':
    f = open('.auth', 'r')
    USER = f.readline().rstrip()
    PASSWORD = f.readline().rstrip()
    f.close()

j = jenkins.Jenkins('http://jenkins.dimagi.com', USER, PASSWORD)

job_roots = ['javarosa-core-library', 'commcare-mobile', 'commcare-odk']
main_jenkins_server = '162.242.212.212'
server_user = 'pmates'

# None -> String
def create_new_release_jobs():
    version = get_next_release_version()

    last_release = version.get_last_version_short()
    for job_root in job_roots:
        create_new_release_job(job_root, last_release, version)

    set_build_numbers(version)
    inc_minor_version('commcare-mobile')
    inc_minor_version('commcare-mobile-{}'.format(version.short_string()))

    return version.short_string()

# None -> Version
def get_next_release_version():
    """
    Reads the version number off of the commcare-mobile job, which should be
    set to the next release.
    """
    xml = j.get_job_config('commcare-mobile')

    versionPattern = re.compile(r'VERSION=(\d+).(\d+).(\d+)')
    current_version_raw = versionPattern.search(xml).groups()
    if len(current_version_raw) != 3:
        raise Exception("Couldn't find next version to deploy")
    return Version(*map(int, current_version_raw))

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

    staged_release_job = 'commcare-mobile-{}'.format(next_version.get_last_version_short())
    release_xml = j.get_job_config(staged_release_job )
    current_version_raw = versionPattern.search(release_xml).groups()
    if len(current_version_raw) != 3:
        raise Exception("Couldn't find next version to deploy")
    return Version(*map(int, current_version_raw))

# String String Version -> None
def create_new_release_job(base_job_name, last_release, new_release_version):
    last_release_job_name = '{}-{}'.format(base_job_name, last_release)
    print("last release job name: {}".format(last_release_job_name))
    xml = j.get_job_config(last_release_job_name)

    new_version = new_release_version.short_string()
    print("new version short: {}".format(new_version))

    xml = replace_references_to_old_jobs(xml, last_release, new_version)

    old_tag_name = get_old_git_tag(xml)
    print("old git tag: {}".format(old_tag_name))

    xml = xml.replace(old_tag_name, 'refs/heads/commcare_{}'.format(new_version))

    new_release_job_name = '{}-{}'.format(base_job_name, new_version)
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
    update_build_number('commcare-mobile', new_version, 1)
    update_build_number('commcare-odk', new_version, 1)
    update_build_number('commcare-mobile', 2000)
    update_build_number('commcare-odk', 2000)

# String Version Integer -> None
def update_build_number(job_base, current_version, increment_by):
    old_job = '{}-{}'.format(job_base, current_version.get_last_version_short())
    new_job = '{}-{}'.format(job_base, current_version.short_string())
    current_build_number = j.get_job_info(old_job)['nextBuildNumber']

    print('build number for {}: {}'.format(old_job, current_build_number))

    f = open('nextBuildNumber', 'w', encoding='utf-8')
    next_build_number = int(current_build_number) + increment_by
    f.write('{}\n'.format(next_build_number))
    f.close()

    try:
        subprocess.call('scp nextBuildNumber {0}@{1}:/var/lib/jenkins/jobs/{2}/nextBuildNumber'.format(server_user, main_jenkins_server, new_job), shell=True)
    except Exception:
        print('Failed setting nextBuildNumber for {}'.format(new_job))
        print("Please manually set {}'s nextBuildNumber to {} at \n http://jenkins.dimagi.com/job/{}/nextbuildnumber/".format(new_job, next_build_number, new_job))

    os.remove('nextBuildNumber')

    # make jenkins read the build number change from memory
    reload_job_into_jenkins_memory(new_job)

def reload_job_into_jenkins_memory(job_name):
    xml = j.get_job_config(job_name)
    j.reconfig_job(job_name, xml)

# String -> None
def inc_minor_version(job_name):
    xml = j.get_job_config(job_name)
    versionPattern = re.compile(r'VERSION=(\d+).(\d+).(\d+)')
    current_version_raw = versionPattern.search(xml).groups()

    if len(current_version_raw) != 3:
        raise Exception("Couldn't parse version")
    current_version = Version(*map(int, current_version_raw))
    next_minor_version = current_version.get_next_minor_release()

    print('changing {} version reference {} to {}'.format(job_name, current_version, next_minor_version))

    xml = xml.replace("VERSION={}".format(current_version), "VERSION={}".format(next_minor_version))

    j.reconfig_job(job_name, xml)

# String -> None
def inc_hotfix_version(version):
    job_name = "commcare-mobile-{}".format(version.short_string())
    xml = j.get_job_config(job_name)
    versionPattern = re.compile(r'VERSION=(\d+).(\d+).(\d+)')
    current_version_raw = versionPattern.search(xml).groups()

    if len(current_version_raw) != 3:
        raise Exception("Couldn't parse version")
    current_version = Version(*map(int, current_version_raw))
    next_hotfix_version = current_version.get_next_hotfix()

    print('changing {} version reference {} to {}'.format(job_name, current_version, next_hotfix_version))

    xml = xml.replace("VERSION={}".format(current_version), "VERSION={}".format(next_hotfix_version))

    j.reconfig_job(job_name, xml)


def update_job_with_hotfix(current_version):
    return

# String String -> None
def make_release_jobs_use_tags(branch, tag):
    for job_root in job_roots:
        make_release_job_use_tag(job_root, branch, tag)

# String Version String -> None
def make_release_job_use_tag(base_job_name, branch, tag):
    job_name = '{}-{}'.format(base_job_name, last_release)

    print("update {} to build off tag {}".format(job_name, tag))

    xml = j.get_job_config(job_name)
    xml = xml.replace("refs/heads/{}".format(branch),
            "refs/tags/{}".format(tag))

    j.reconfig_job(job_name, xml)

#create_new_release_jobs()
