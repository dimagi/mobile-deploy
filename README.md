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
