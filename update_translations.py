import subprocess
import os
import deploy_config as conf
import xml.etree.ElementTree as ET

# name of the master hq translations file to be updated
hq_translations_filename = 'messages_en-2.txt'

# relative path to the subfolder within the javarosa repo containing the messages_default.txt file
javarosa_subfolder = './j2me/shared-resources/resources'

# relative path to the subfolder within the commcare repo containing the messages_cc_default.txt file
commcare_subfolder = './application/resources'

# relative path to the subfolder within the commcare-odk repo containing the messages_ccodk_default.txt file
ccodk_messages_subfolder = './app/assets/locales'

# relative path to the subfolder within the commcare-odk repo containing the strings.xml file
ccodk_strings_subfolder = './app/res/values'

javarosa_repo = 'javarosa'
commcare_repo = 'commcare'
commcare_odk_repo = 'commcare-odk'
translations_repo = 'commcare-translations'

javarosa_filename = 'messages_default.txt'
commcare_filename = 'messages_cc_default.txt'
ccodk_messages_filename = 'messages_ccodk_default.txt'
ccodk_strings_filename = 'strings.xml'

all_filenames = [javarosa_filename, commcare_filename, ccodk_messages_filename, ccodk_strings_filename]
all_repos = [javarosa_repo, commcare_repo, commcare_odk_repo, translations_repo]

strings_namespace = '{http://strings_namespace}'
github_url = 'https://github.com/dimagi/commcare-translations/compare/'


def update_translations(new_version_number):
    if unstaged_changes_present():
        raise Exception("One of your repositories has un-staged changes, please stash them and try again")
    new_javarosa_text = get_updated_translations(javarosa_repo, javarosa_subfolder, javarosa_filename)
    new_commcare_text = get_updated_translations(commcare_repo, commcare_subfolder, commcare_filename)
    new_ccodk_text = get_updated_translations(commcare_odk_repo, ccodk_messages_subfolder, ccodk_messages_filename)
    new_strings_text = get_updated_strings_block()
    new_text_blocks = [new_javarosa_text, new_commcare_text, new_ccodk_text, new_strings_text]

    new_branch_name = checkout_new_translations_branch(new_version_number)
    backup_old_translations_file()
    create_updated_translations_file(new_text_blocks)
    commit_and_push_new_branch(new_version_number, new_branch_name)


def unstaged_changes_present():
    for repo in all_repos:
        chdir_repo(repo)
        if b'' != subprocess.check_output("git status -s | sed '/^??/d'", shell=True):
            # If the results of git status are non-empty
            return True
    return False


def checkout_new_translations_branch(new_version_number):
    chdir_repo(translations_repo)
    subprocess.call('git checkout master', shell=True)
    subprocess.call('git pull origin master', shell=True)
    new_branch_name = '{}_release_additions'.format(new_version_number)
    subprocess.call('git checkout -b {}'.format(new_branch_name), shell=True)
    return new_branch_name


def backup_old_translations_file():
    os.rename(hq_translations_filename, hq_translations_filename + '.bak')


# Write all of the updated text blocks from the 4 mobile translations files to the master hq translations file, with
# headers for each section
def create_updated_translations_file(new_text_blocks):
    header_prefix = '# *** '
    header_suffix = ' ***'
    with open(hq_translations_filename, 'w') as f:
        os.utime(hq_translations_filename, None)
        num_blocks = len(all_filenames)
        for i in range(num_blocks):
            f.write(header_prefix + all_filenames[i] + header_suffix + '\n\n')
            f.write(new_text_blocks[i])
            if i < num_blocks-1:
                f.write('\n\n')


def commit_and_push_new_branch(new_version_number, new_branch_name):
    subprocess.call('git add {}'.format(hq_translations_filename), shell=True)
    commit_message = 'Auto-commit: Update translations file for CommCare release ' + new_version_number
    subprocess.call("git commit -m '{}'".format(commit_message),
                    shell=True)
    subprocess.call('git push origin {}'.format(new_branch_name), shell=True)
    print('An updated translations file has been pushed to GitHub as branch {0}. To create a PR out of this '
          'branch, you can go directly to {1}'.format(new_branch_name, github_url + new_branch_name))


# Return a string containing the updated text that should go into the master hq translations file from the given file
def get_updated_translations(repo, relative_path, filename):
    chdir_repo(repo)
    subprocess.call('git checkout master', shell=True)
    os.chdir(relative_path)
    with open(filename, 'r') as f:
        return f.read().strip()


# Return a string containing the updated text that should go into the master hq translations file from the strings.xml
# file in the mobile codebase. Because it is an xml file instead of a plain text file, the extraction needs to be done
# in a different way from all of the other files
def get_updated_strings_block():
    chdir_repo(commcare_odk_repo)
    subprocess.call('git checkout master', shell=True)
    os.chdir(ccodk_strings_subfolder)
    tree = ET.parse(ccodk_strings_filename)
    resources = tree.getroot()
    string_list = []
    for string in resources.findall('string'):
        translatable_value = string.get('{}translatable'.format(strings_namespace))
        if translatable_value == 'true':
            name = string.get('name')
            value = string.text
            if name is not None and value is not None:
                name_with_prefix = 'odk_{}'.format(name)
                string_list.append(name_with_prefix + '=' + value + '\n')
    return "".join(string_list)


def chdir_repo(repo):
    os.chdir(os.path.join(conf.BASE_DIR, repo))