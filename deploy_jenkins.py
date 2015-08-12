#!/bin/python
import jenkins, re
import subprocess
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
    version = find_release_version()

    last_release = version.get_last_version_short()
    for job_root in job_roots:
        create_new_release_job(job_root, last_release, version)

    # set_build_numbers(version)
    # inc_version_number('commcare-mobile')
    # inc_version_number('commcare-mobile-2.23')
    return version.short_string()

# None -> Version
def find_release_version():
    """
    Reads the version number off of the commcare-mobile job, which should be
    set to the next release.
    """
    xml = j.get_job_config('commcare-mobile')

    versionPattern = re.compile(r'VERSION=(\d+).(\d+).(\d+)')
    next_version_raw = versionPattern.search(xml).groups()
    if len(next_version_raw) != 3:
        raise Exception("Couldn't find next version to deploy")
    return Version(*map(int, next_version_raw))

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

    #from pdb import set_trace; set_trace()
    xml = xml.replace(old_tag_name, 'refs/heads/commcare_{}'.format(new_version))

    new_release_job_name = '{}-{}'.format(base_job_name, new_version)
    j.create_job(new_release_job_name, xml)

def replace_references_to_old_jobs(xml, last_release, new_version):
    #from pdb import set_trace; set_trace()
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

def set_build_numbers(new_version):
    update_build_number('commcare-mobile-{}'.format(new_version.short_string()), 1)
    update_build_number('commcare-odk-{}'.format(new_version.short_string()), 1)
    update_build_number('commcare-mobile', 2000)
    update_build_number('commcare-odk', 2000)

def update_build_number(base_job, increment_by):
    current_build_number = j.get_job_info(base_job)['nextBuildNumber']
    f = open('nextBuildNumber', 'w', encoding='utf-8')
    f.write(str(current_build_number + increment_by))
    f.close()
    subprocess.call('scp nextBuildNumber {0}@{1}:/var/lib/jenkins/jobs/{2}/nextBuildNumber'.format(server_user, main_jenkins_server, base_job))
    os.remove('nextBuildNumber')

# String -> None
def inc_version_number(job_name):
    xml = j.get_job_config(job_name)
    versionPattern = re.compile(r'VERSION=(\d+).(\d+).(\d+)')
    next_hotfix_raw = versionPattern.search(xml).groups()

    if len(next_hotfix_raw) != 3:
        raise Exception("Couldn't parse version")
    next_hotfix_version = Version(*map(int, next_version_raw))
    next_minor_version = next_hotfix_version.get_next_minor_release()
    xml.replace("VERSION={}".format(next_hotfix_version.full_string()),
            "VERSION={}".format(next_minor_version.full_string()))

    j.reconfig_job(job_name, xml)


def update_job_with_hotfix(current_version):
    return

def update_main_job():
    # TODO: bump version number of commcare-mobile.
    return

create_new_release_jobs()
