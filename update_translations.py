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

header_prefix = '# *** '
header_suffix = ' ***'

strings_namespace = '{http://strings_namespace}'


def update_translations(new_version_number):
    new_javarosa_text = get_updated_translations(javarosa_repo, javarosa_subfolder, javarosa_filename)
    new_commcare_text = get_updated_translations(commcare_repo, commcare_subfolder, commcare_filename)
    new_ccodk_text = get_updated_translations(commcare_odk_repo, ccodk_messages_subfolder, ccodk_messages_filename)
    new_strings_text = get_updated_strings_block()
    new_text_blocks = [new_javarosa_text, new_commcare_text, new_ccodk_text, new_strings_text]

    new_branch_name = checkout_new_translations_branch(new_version_number)
    backup_old_translations_file()
    create_updated_translations_file(new_text_blocks)
    commit_and_push_new_branch(new_version_number, new_branch_name)


def checkout_new_translations_branch(new_version_number):
    chdir_repo(translations_repo)
    subprocess.call('git checkout master', shell=True)
    subprocess.call('git pull origin master', shell=True)
    new_branch_name = '{}_release_additions'.format(new_version_number)
    subprocess.call('git checkout -b {}'.format(new_branch_name), shell=True)
    return new_branch_name


def backup_old_translations_file():
    os.rename(hq_translations_filename, hq_translations_filename + '.bak')


def create_updated_translations_file(new_text_blocks):
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
    subprocess.call("git commit -m '{}'".format('Auto-commit: Update translations file for CommCare release ' + new_version_number),
                    shell=True)
    subprocess.call('git push origin {}'.format(new_branch_name), shell=True)


def get_updated_translations(repo, relative_path, filename):
    chdir_repo(repo)
    subprocess.call('git checkout master', shell=True)
    os.chdir(relative_path)
    with open(filename, 'r') as f:
        return f.read().strip()


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