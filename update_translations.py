import subprocess
import os
import deploy_config as conf
import xml.etree.ElementTree as ET

# relative path to the messages_default.txt file within the javarosa repo
javarosa_relative_path = './j2me/shared-resources/resources'

# relative path to the messages_cc_default.txt file within the commcare repo
commcare_relative_path = './application/resources'

# relative path to the messages_ccodk_default.txt file within the commcare-odk repo
ccodk_default_relative_path = './app/assets/locales'

# relative path to the strings.xml file within the commcare-odk repo
ccodk_strings_relative_path = './app/res/values'


def update_translations():
    new_javarosa_text = get_updated_translations('javarosa', javarosa_relative_path, 'messages_default.txt')
    new_commcare_text = get_updated_translations('commcare', commcare_relative_path, 'messages_cc_default.txt')
    new_ccodk_text = get_updated_translations('commcare-odk', ccodk_default_relative_path, 'messages_ccodk_default.txt')
    new_strings_text = get_updated_strings_block()


def get_updated_translations(repo, relative_path, filename):
    chdir_repo(repo)
    os.chdir(relative_path)
    f = open(filename, 'r')
    return f.read()


# None -> String
def get_updated_strings_block():
    chdir_repo('commcare-odk')
    os.chdir(ccodk_strings_relative_path)
    tree = ET.parse('strings.xml')
    resources = tree.getroot()
    string_list = []
    for string in resources.findall('string'):
        name = string.get('name')
        value = string.text
        if name is not None and value is not None:
            string_list.append(name + '=' + value + '\n')
    print("".join(string_list))




# String -> None
def chdir_repo(repo):
    os.chdir(os.path.join(conf.BASE_DIR, repo))


# None -> None
def chdir_base():
    os.chdir(conf.BASE_DIR)


update_translations()