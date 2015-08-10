#!/bin/python

import deploy_jenkins, deploy_git

def create_release():
    version = deploy_jenkins.create_new_release_jobs()
    deploy_git.create_new_branches(version)
    return

def create_hotfix():
    return

def deploy_hotfix():
    return

def deploy_release():
    return
