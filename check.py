import os
import subprocess

import jenkins_utils
import utils as util

from deploy_config import BASE_DIR, REPOS, BRANCH_BASE


def run_checks():
    """
    Read-only preflight for 'deploy create': reports what the scripts will see
    without changing anything on Jenkins, GitHub or the local repositories.
    """
    problems = []

    def report(ok, message):
        print('{} {}'.format('OK  ' if ok else 'FAIL', message))
        if not ok:
            problems.append(message)

    missing = [r for r in REPOS if not os.path.isdir(os.path.join(BASE_DIR, r))]
    report(not missing, 'repositories found under {}{}'.format(
        BASE_DIR, '' if not missing else ' (missing: {})'.format(missing)))
    if missing:
        return problems

    version = jenkins_utils.get_next_release_version()
    last_release = version.get_last_version_short()
    print('INFO next release from Jenkins: {}, last release: {}'.format(
        version, last_release))

    for job_root in jenkins_utils.job_roots:
        last_job = '{}-{}'.format(job_root, last_release)
        new_job = '{}-{}'.format(job_root, version.short_string())
        report(bool(jenkins_utils.j.job_exists(last_job)),
               '{} exists'.format(last_job))
        report(not jenkins_utils.j.job_exists(new_job),
               '{} does not exist yet'.format(new_job))
        try:
            tag = jenkins_utils.get_old_tag_version(
                jenkins_utils.j.get_job_config(last_job))
            report(True, '{} builds from tag commcare_{}'.format(last_job, tag))
        except Exception as e:
            report(False, '{}: {}'.format(last_job, e))

    branch = '{}{}'.format(BRANCH_BASE, version.short_string())
    report(not util.branch_exists_in_repos(branch, REPOS),
           'branch {} does not exist on GitHub yet'.format(branch))

    report(not util.unstaged_changes_present(REPOS),
           'no uncommitted changes in {}'.format(', '.join(REPOS)))

    for repo in REPOS:
        util.chdir_repo(repo)
        subprocess.check_call(['git', 'fetch', '-q', 'origin', 'master'])
        current = subprocess.check_output(
            ['git', 'branch', '--show-current'], text=True).strip()
        behind = subprocess.check_output(
            ['git', 'rev-list', '--count', 'master..origin/master'],
            text=True).strip()
        util.chdir_base()
        print('INFO {} is on branch {}; local master is {} commit(s) behind '
              'origin (create checks out and fast-forwards master)'.format(
                  repo, current, behind))

    print()
    if problems:
        print('{} problem(s) found; fix them before running create.'.format(
            len(problems)))
    else:
        print('All checks passed.')
    return problems
