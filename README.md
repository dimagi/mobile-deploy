# Automated deploy scripts for CommCare
The [CommCare mobile release process](https://confluence.dimagi.com/display/MD/CommCare+Release+Process) has now been mostly automated!

Here is what you need to do to get started:

* Create a user on the jenkins master machine that is part of "jenkins" group
* Add your ssh public key to that machine so that you can login without typing your password. This is need to push files to that server via the deploy scripts you run locally.
* Checkout the [mobile deploy repository](https://github.com/dimagi/mobile-deploy) and copy deploy.conf.template to deploy.conf and populate it.

Deploy process is now:

* `./deploy create`
* Follow __Make new build available on HQ__ instructions on [release page](https://confluence.dimagi.com/display/MD/CommCare+Release+Process) 
* Run QA
* `./deploy release`
* Follow __Perform the Release__ instructions on [release page](https://confluence.dimagi.com/display/MD/CommCare+Release+Process)
* Follow __Reconcile Branches__ instructions on [release page](https://confluence.dimagi.com/display/MD/CommCare+Release+Process)

Soon there will be hotfix automation too
