#!/bin/python
import subprocess, os, re

branch_base = 'commcare_'

repos = ['javarosa', 'commcare', 'commcare-odk']

# String -> None
def create_new_branches(version):
    if unstagedChangesPresent():
        raise Exception("one of the branches has unstaged changes, please stash and try again")
    pullMasters()

    branch_name = "{}{}".format(branch_base, version)
    if branchExistsInRepos(branch_name):
        raise Exception("commcare_{} branch already exists".format(version))

    createReleaseBranches(version)
    updateVersionNumbers()

def unstagedChangesPresent():
    for repo in repos:
        os.chdir(repo)
        if b'' != subprocess.check_output("git status -s | sed '/^??/d'", shell=True):
            return True
        os.chdir('../')
    return False

def pullMasters():
    for repo in repos:
        os.chdir(repo)
        subprocess.call('git pull origin master', shell=True)
        os.chdir('../')

def branchExistsInRepos(branch_name):
    for x in [branchExists(repo, branch_name) for repo in repos]:
        if x:
            return True
    return False

def branchExists(child_directory, branch_name):
    os.chdir(child_directory)
    try:
        subprocess.check_output('git show-ref ' + branch_name, shell=True)
        return True
    except subprocess.CalledProcessError:
        return False
    finally:
        os.chdir('../')

def createReleaseBranches(branch_name):
    for repo in repos:
        os.chdir(repo)
        subprocess.call('git checkout -b ' + branch_name, shell=True)
        subprocess.call('git push origin ' + branch_name, shell=True)
        os.chdir('../')

def updateVersionNumbers():
    updateCommCareVersionNumbers()
    updateOdkVersionNumbers()

def updateCommCareVersionNumbers():
    os.chdir('commcare')
    subprocess.call('git checkout master', shell=True)

    replace_func(replace_build_prop, 'application/build.properties')
    replace_func(replace_config_engine_version,
            'util/src/org/commcare/util/CommCareConfigEngine.java')

    subprocess.call('git add -u', shell=True)
    subprocess.call("git commit -m 'Automated version bump'", shell=True)
    subprocess.call("git push origin master", shell=True)
    os.chdir('../')

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
    if result != None:
        version = result.groups()
        next_version_raw = map(int, version)
        next_version_raw[-1] = next_version_raw[-1] + 1
        next_version = Version(*next_version_raw)
    else:
        versionPattern = re.compile(r'app.version=(\d+).(\d+)$')
        version = versionPattern.search(file_contents).groups()
        next_version_raw = map(int, version)
        next_version_raw[-1] = next_version_raw[-1] + 1
        next_version = Version(next_version_raw[0], next_version_raw[1], 0)
    return file_contents.replace('app.version={}'.format(next_version),
            'app.version={}'.format(next_version.get_next_minor_release))

# String -> String
def replace_config_engine_version(file_contents):
    versionPattern = re.compile(r'CommCarePlatform\((\d+), (\d+)\)')
    result = versionPattern.search(file_contents)
    if result == None:
        raise Exception("Couldn't parse version")
    version = versionPattern.search(file_contents).groups()
    next_version_raw = map(int, version)
    next_version_raw[-1] = next_version_raw[-1] + 1
    next_version = Version(next_version_raw[0], next_version_raw[1], 0)

    return file_contents.replace('CommCarePlatform({}, {})'.format(next_version.major, next_version.minor), 'CommCarePlatform({}, {})'.format(next_version.major, next_version.minor + 1))

def updateOdkVersionNumbers():
    os.chdir('commcare-odk')
    subprocess.call('git checkout master', shell=True)

    replace_func(update_manifest_version, 'app/AndroidManifest')

    subprocess.call('git add -u', shell=True)
    subprocess.call("git commit -m 'Automated version bump'", shell=True)
    subprocess.call("git push origin master", shell=True)
    os.chdir('../')

# String -> String
def update_manifest_version(file_contents):
    versionPattern = re.compile(r'android:versionName="(\d+).(\d+)"')
    result = versionPattern.search(file_contents)
    if result == None:
        raise
    version = versionPattern.search(file_contents).groups()
    next_version = map(int, version)
    current_version = 'android:versionName="{}.{}"'.format(next_version[0], next_version[1])
    next_version = 'android:versionName="{}.{}"'.format(next_version[0], next_version[1] + 1)
    return file_contents.replace(current_version, next_version)

# String -> None
def update_resource_string_version():
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
            on_version_line = 42
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
