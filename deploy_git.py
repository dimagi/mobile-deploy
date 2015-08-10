#!/bin/python
import subprocess, os, re

branch_base = 'commcare_'

repos = ['javarosa', 'commcare', 'commcare-odk']

# String -> None
def create_new_branches(version):
    if unstagedChangesPresent():
        print("one of the branches has unstaged changes, please stash and try again")
        raise
    pullMasters()

    branch_name = "{}{}".format(branch_base, version)
    if branchExistsInRepos(branch_name):
        print("commcare_{} branch already exists".format(version))
        raise

    createReleaseBranches(version)

def pullMasters():
    for repo in repos:
        os.chdir(repo)
        subprocess.call('git pull origin master', shell=True)
        os.chdir('../')

def unstagedChangesPresent():
    for repo in repos:
        os.chdir(repo)
        if b'' != subprocess.check_output("git status -s | sed '/^??/d'", shell=True):
            return True
        os.chdir('../')
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

def branchExistsInRepos(branch_name):
    for x in [branchExists(repo, branch_name) for repo in repos]:
        if x:
            return True
    return False

def createReleaseBranches(branch_name):
    for repo in repos:
        os.chdir(repo)
        subprocess.call('git checkout -b ' + branch_name, shell=True)
        subprocess.call('git push origin ' + branch_name, shell=True)
        os.chdir('../')

def updateVersionNumbers():
    os.chdir('commcare')
    subprocess.call('git checkout master', shell=True)

    # TODO: stopped here
    read_file = open('application/build.properties', 'r')
    write_file = open('application/build.properties.new', 'w')

    versionPattern = re.compile(r'app.version=(\d+).(\d+).(\d+)')
    next_version_raw = versionPattern.search(xml).groups()
    write_file.write()
    read_file.close()
    write_file.close()
    os.rename('application/build.properties.new', 'application/build.properties')

    subprocess.call('git add -u', shell=True)
    subprocess.call("git commit -m 'Automated version bump'", shell=True)
    subprocess.call("git push origin master", shell=True)
    os.chdir('../')
    """
    commcare
        application/build.properties: app.version, 
        util/src/org/commcare/util/CommCareConfigEngine.java getMinorVersion(), 
    commcare-odk
        app/AndroidManifest - versionName
        app/res/values/strings.xml - commcare_version integer array object
    """

[pullMaster(repo) for repo in repos]

print(branchExistsInRepos())
