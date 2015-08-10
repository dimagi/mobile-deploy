#!/bin/python
import jenkins, re

USER = ''
PASSWORD = ''
j = jenkins.Jenkins('http://jenkins.dimagi.com', USER, PASSWORD)

job_roots = ['javarosa-core-library-', 'commcare-mobile-', 'commcare-odk-']
main_jenkins_server = '162.242.212.212'
server_user = 'pmates'

# None -> String
def create_new_release_jobs():
    version = find_release_version()

    last_release = version.get_last_version_short()
    for job_root in job_roots:
        create_new_release_job(job_root, last_release, version)

    set_build_numbers(version)
    inc_version_number('commcare-mobile')
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
        print("Couldn't find next version to deploy")
        raise
    return Version(*map(int, next_version_raw))

# String -> None
def inc_version_number(job_name):
    xml = j.get_job_config(job_name)
    versionPattern = re.compile(r'VERSION=(\d+).(\d+).(\d+)')
    next_hotfix_raw = versionPattern.search(xml).groups()

    if len(next_hotfix_raw) != 3:
        raise
    next_hotfix_version = Version(*map(int, next_version_raw))
    next_minor_version = next_hotfix_version.get_next_minor_release()
    xml.replace("VERSION={}".format(next_hotfix_version.full_string()),
            "VERSION={}".format(next_minor_version.full_string()))

    j.reconfig_job(job_name, xml)


# String String Version -> None
def create_new_release_job(base_job_name, last_release, new_release_version):
    last_release_job_name = '{}-{}'.format(base_job_name, last_release)
    xml = j.get_job_config(last_release_job_name)

    new_version = new_release_version.short_string()

    for job_base in job_roots:
        xml.replace('{}-{}'.format(job_base, last_release),
                '{}-{}'.format(job_base, new_version))

    versionPattern = re.compile(r'VERSION=(\d+).(\d+).(\d+)')
    next_hotfix_raw = versionPattern.search(xml).groups()

    if len(next_hotfix_raw) != 3:
        raise

    tag_name_version = Version(*map(int, next_version_raw)).get_last_hotfix().full_string()

    xml.replace('refs/tags/commcare_{}'.format(tag_name_version),
            'refs/heads/commcare_{}'.format(new_version))

    new_release_job_name = '{}-{}'.format(base_job_name, new_version)
    j.create_job(new_release_job_name, xml)


def set_build_numbers(new_version):
    update_build_number('commcare-mobile-{}'.format(new_version.short_string()), 1)
    update_build_number('commcare-odk-{}'.format(new_version.short_string()), 1)
    update_build_number('commcare-mobile', 2000)
    update_build_number('commcare-odk', 2000)

def update_build_number(base_job, increment_by):
    current_build_number = j.get_job_info(base_job)['nextBuildNumber']
    f = open('nextBuildNumber', 'w')
    f.write(str(current_build_number + increment_by))
    f.close()
    subprocess.call('scp nextBuildNumber {0}@{1}:/var/lib/jenkins/jobs/{2}/nextBuildNumber'.format(server_user, main_jenkins_server, base_job))
    os.remove('nextBuildNumber')

def update_job_with_hotfix(current_version):
    return

def update_main_job():
    # TODO: bump version number of commcare-mobile.
    return


class Version:
    def __init__(self, major, minor, hotfix):
        self.major = major
        self.minor = minor
        self.hotfix = hotfix

    def full_string():
        return "{0}.{1}.{2}".format(self.major, self.minor, self.hotfix)

    def short_string():
        return "{0}.{1}".format(self.major, self.minor)

    def get_next_minor_release():
        return Version(self.major, self.minor + 1, 0)

    def get_next_major_release():
        return Version(self.major + 1, 0, 0)

    def get_next_hotfix():
        return Version(self.major, self.minor, self.hotfix + 1)

    def get_last_hotfix():
        return Version(self.major, self.minor, self.hotfix - 1)

    def get_last_version_short():
        if self.minor == 0:
            return Version(self.major - 1, 0, 0).short_string()
        else:
            return Version(self.major, self.minor - 1, 0).short_string()

