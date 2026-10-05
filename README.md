# Automated deploy scripts for CommCare
These scripts automate the git and Jenkins steps of the [CommCare Release Checklist](https://dimagi.atlassian.net/wiki/spaces/cc/pages/2145059319/CommCare+Release+Checklist). They run on macOS, Linux and Windows.

## setup
* Clone `commcare-android`, `commcare-core` and `commcare-translations` side by side in one folder. `deploy finalize` needs `commcare-translations`.
* Clone this repository, copy `deploy.conf.template` to `deploy.conf` and fill it in:
  * `dimagi_projects_dir` is the folder holding the repositories above. On Windows, use forward slashes, e.g. `C:/code/dimagi`.
  * `user` is your Jenkins username (your GitHub username) and `password` is a Jenkins API token, found under "Security" in your Jenkins user settings.
* Install the requirements into a virtual environment with Python 3.8 or newer:

  macOS / Linux:
  ```
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  ```
  Windows:
  ```
  py -3 -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
  ```

Run the scripts with the environment's Python: `.venv/bin/python deploy <command>` on macOS / Linux, `.venv\Scripts\python deploy <command>` on Windows. With the environment activated, `./deploy <command>` also works on macOS / Linux.

## deploy

`deploy help` will give you argument descriptions.

The workflow:
* Temporarily rename the `master` branch protection rule in [commcare-android](https://github.com/dimagi/commcare-android/settings/branches) and [commcare-core](https://github.com/dimagi/commcare-core/settings/branches), since the scripts push version bumps straight to `master`. Rename it back afterwards.
* `deploy check` reports what `create` will see without changing anything: the next version from Jenkins, the jobs and branches that should and shouldn't exist yet, and the state of your local repositories. Fix anything it flags.
* `deploy create` creates the release jobs and branches. Local `master` must have no uncommitted changes; the script checks out and fast-forwards `master` itself.
* Follow __Make new build available on HQ__ on the release checklist
* Run QA
* `deploy release`
* Wait for builds to complete (might have to trigger them). Lock in and name the builds with the CommCare version
* Follow __Publish to PlayStore__ on the release checklist
* Follow __Reconcile Branches__ on the release checklist
* `deploy finalize`

## hotfix
`hotfix help` will give you argument descriptions. 

The workflow:
* `hotfix create`
* perform hotfix dev work, merging into the branch created by the above command
* `hotfix release`
* Wait for builds to complete (might have to trigger them). Lock in and name the builds with the CommCare version
* `hotfix finalize`

In case you need to do work on other branches while in the middle of a hotfix, you can always resume hotfix work by running `hotfix resume`. This will checkout hotfix branches created in the `create` step and latest release tags for the remaining branches.

## TODO
* auto-compile release notes from PRs
* would be nice to automatically name and lock in jenkins builds triggered by the deploy scripts

## architecture overview
Mobile deploy does 3 things:

 * Manipulates git state using local repositories and manually calling git commands via a python shell interface.
 * Creates new jenkins jobs and manipulates the state of existing jobs using the jenkins python plugin. Jenkins jobs are represented using an XML data structure, so job manipulations usually involve pulling existing XML and running search/replaces over them.
 * Sets Jenkins job build numbers through the Jenkins API

One major complexity of the deploy system is version numbers. Since there is no central place that tracks the current CommCare release version, we pull the version from several different places.

 * When we want to get the last hotfixed version, we do so by parsing the release git tags in the given repository, which should always be something like `commcare_2.23.0`.
 * When we create a jenkins job for the next release, we pull the `VERSION` environment variable set in the `commcare-android` jenkins job, which is always set to the next unreleased CommCare version.

Things to watch out for

 * The scripts manipulate git tags using local versions of the code repositories. It is possible to mess things up if you are in the middle of running a part of the release and decide to checkout a branch or make changes to the code base. In the future it would be good to migrate the scripts to run on a server so that we don't have to worry about this issue.
