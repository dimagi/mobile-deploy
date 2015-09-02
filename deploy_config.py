import ConfigParser from configparser

config = ConfigParser()
config.read("deploy.conf")

JENKINS_USER = config.get('Jenkins', 'user')
JENKINS_PASSWORD = config.get('Jenkins', 'password')

BUILD_SERVER_USER = config.get('BuildServer', 'user')
BUILD_SERVER = config.get('BuildServer', 'addr')

BASE_DIR = config.get('Local', 'dimagi_projects_dir')
