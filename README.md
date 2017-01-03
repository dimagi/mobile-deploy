# Automated deploy scripts for CommCare
The [CommCare mobile release process](https://confluence.dimagi.com/display/MD/CommCare+Release+Process) has now been mostly automated!

## setup
* Create a user on the jenkins master machine that is part of "jenkins" group:
`useradd -m -g users -G jenkins,sudo -s /bin/zsh yolandi` and `passwd yolandi`
* Add your ssh public key to that machine so that you can login without typing your password. [First few steps here detail this](https://help.github.com/articles/generating-ssh-keys/). This is need to push files to that server via the deploy scripts you run locally.
* Checkout the [mobile deploy repository](https://github.com/dimagi/mobile-deploy) and copy deploy.conf.template to deploy.conf and populate it the correct credentials.
* `pip install -r requirements.txt`

## deploy

`./deploy help` will give you argument descriptions. 

The workflow:
* Make sure that your local master branch for both repos does not have any unstaged changes.
* `./deploy create`
* Follow __Make new build available on HQ__ instructions on [release page](https://confluence.dimagi.com/display/MD/CommCare+Release+Process) 
* Run QA
* `./deploy release`
* Wait for builds to complete (might have to trigger them). Lock in and name the builds with the CommCare version
* Follow __Perform the Release__ instructions on [release page](https://confluence.dimagi.com/display/MD/CommCare+Release+Process)
* Follow __Reconcile Branches__ instructions on [release page](https://confluence.dimagi.com/display/MD/CommCare+Release+Process)
* `./deploy finalize`

## hotfix
`./hotfix help` will give you argument descriptions. 

The workflow:
* `./hotfix create`
* perform hotfix dev work, merging into the branch created by the above command
* `./hotfix release`
* Wait for builds to complete (might have to trigger them). Lock in and name the builds with the CommCare version
* `./hotfix finalize`

In case you need to do work on other branches while in the middle of a hotfix, you can always resume hotfix work by running `./hotfix resume`. This will checkout hotfix branches created in the `create` step and latest release tags for the remaining branches.

## TODO
* the code that adds/removs jobs from jenkins views doesn't seem to be working
* auto-compile release notes from PRs
* would be nice to automatically name and lock in jenkins builds triggered by the deploy scripts

## architecture overview
Mobile deploy does 3 things:

 * Manipulates git state using local repositories and manually calling git commands via a python shell interface.
 * Creates new jenkins jobs and manipulates the state of existing jobs using the jenkins python plugin. Jenkins jobs are represented using an XML data structure, so job manipulations usually involve pulling existing XML and running search/replaces over them.
 * Pushes files to the jenkins server via SSH in a order to set jenkins job build numbers

One major complexity of the deploy system is version numbers. Since there is no central place that tracks the current CommCare release version, we pull the version from several different places.

 * When we want to get the last hotfixed version, we do so by parsing the release git tags in the given repository, which should always be something like `commcare_2.23.0`.
 * When we create a jenkins job for the next release, we pull the `VERSION` environment variable set in the `commcare-android` jenkins job, which is always set to the next unreleased CommCare version.

Things to watch out for

 * The scripts manipulate git tags using local versions of the code repositories. It is possible to mess things up if you are in the middle of running a part of the release and decide to checkout a branch or make changes to the code base. In the future it would be good to migrate the scripts to run on a server so that we don't have to worry about this issue.
