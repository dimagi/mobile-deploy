#!/usr/bin/python3

"""
Checkout target repo with branch noted as cross-request dependency for a given
pull request of the source repo.
"""

import github3
import os
import re
import subprocess
import sys


# Repo PR -> String
def getCrossBranch(target_repo, source_pr):
    """
    Get target repo branch name that was labeled as cross-requested in source
    pull request.
    """
    url = "{}/pull/(\d+)".format(target_repo.html_url)
    search_pattern = "[Cc]ross-?(request)?:?(\s?){}".format(url)
    cross_request_search = re.search_pattern(search_pattern, source_pr.body)

    if cross_request_search:
        pr_number = cross_request_search.group(3)
        branch_name = target_repo.pull_request(pr_number).head.ref
        return branch_name
    else:
        return "master"


def main():
    if len(sys.argv) < 4:
        print("Command arg format: [source repo] [PR number] [target repo]")
        sys.exit()

    source_repo_name = sys.argv[1]
    pr_number = int(sys.argv[2])
    target_repo_name = sys.argv[3]

    src_repo = github3.repository('dimagi', source_repo_name)
    target_repo = github3.repository('dimagi', target_repo_name)

    src_pr = src_repo.pull_request(pr_number)
    cross_branch = getCrossBranch(target_repo, src_pr)
    subprocess.call('git clone {}'.format(target_repo.clone_url), shell=True)
    os.chdir(target_repo.name)
    subprocess.call('git checkout {}'.format(cross_branch), shell=True)
    os.chdir('../')

if __name__ == "__main__":
    main()
