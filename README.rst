ci-config
=========
Repository for Jenkins and general CI configuration for RDO.

Using Jenkins Job Builder
-------------------------
Jenkins job builder makes it easier to develop, maintain and version jobs.

To install it::

    pip install jenkins-job-builder

Create your ``config.ini`` from the ``config.ini.sample`` file, according to
your Jenkins configuration, then create/update the jobs, a bit like this::

    git clone https://github.com/rdo-infra/ci-config.git
    cd jenkins
    cp config.ini.sample config.ini
    # Edit config.ini to use your jenkins instance and credentials
    vi config.ini
    jenkins-jobs --conf config.ini update jobs

Jenkins plugins
---------------
There are a number of Jenkins plugins that are required or otherwise nice to
have for best results and to run these jobs with full functionality, here's a
list:

**Required**

* `GIT plugin`_: For cloning repositories and checking out revisions
* `Gerrit Trigger`_: For watching gerrit reviews patchsets and trigger gate
  jobs

**Nice to have**

* `OWASP Markup Formatter Plugin`_: For HTML markup in job descriptions
  (Enable "*Safe HTML*" Markup Formatter in Manage Jenkins -> Configure Global
  security)
* AnsiColor_: For colorized output in Jenkins console
* Timestamper_: For timestamps in Jenkins console

.. _GIT plugin: https://wiki.jenkins-ci.org/display/JENKINS/Git+Plugin
.. _Gerrit Trigger: https://wiki.jenkins-ci.org/display/JENKINS/Gerrit+Trigger
.. _OWASP Markup Formatter Plugin: https://wiki.jenkins-ci.org/display/JENKINS/OWASP+Markup+Formatter+Plugin
.. _AnsiColor: https://wiki.jenkins-ci.org/display/JENKINS/AnsiColor+Plugin
.. _Timestamper: https://wiki.jenkins-ci.org/display/JENKINS/Timestamper

Other required configuration
----------------------------
There's some required Jenkins system and plugin configuration to do which is
not provided by JJB.

Gerrit
~~~~~~
The Gerrit Trigger Plugin requires a Gerrit server to be configured in order to
allow the Jenkins instance to listen to the GerritHub event stream.

This is done in ``Manage Jenkins`` -> ``Gerrit Trigger`` ->
``Add new server``::

    name: rdo-ci-centos # This name is used in the JJB files, it's important.
    hostname: review.gerrithub.io
    frontend url: https://review.gerrithub.io/
    ssh port: 29418
    username: <your gerrithub username>
    email: <your email>
    ssh keyfile: <path to your ssh keyfile>

The remainder of the defaults should be good or up to your discretion.

Jenkins slave: Label
~~~~~~~~~~~~~~~~~~~~
The jobs are set to run on any slave/node with the label ``rdo``. You need to
make sure this is configured on the nodes you want the jobs to run on.

This is done in ``Managed Jenkins`` -> ``Managed Nodes`` -> <*node*> ->
``Configure``::

    labels: rdo

Jenkins slave: CICO environment variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This is **only** required when running jobs on the ci.centos.org
infrastructure. WeIRDO and TripleO-Quickstart leverages python-cicoclient_
which provides an ansible module and CLI client to consume the ephemeral bare
metal provisioning infrastructure.

You need to set your ci.centos.org API key as well as the path to the SSH key
used when connecting to the nodes as environment variables on your slave
node(s).

This is done in ``Managed Jenkins`` -> ``Managed Nodes`` -> <*node*> ->
``Configure`` -> ``Node properties`` -> ``Environment variables`` -> ``Add``::

    name: CICO_API_KEY
    value: <api key>

    name: CICO_SSH_KEY
    value: <path to private key>

.. _python-cicoclient: http://python-cicoclient.readthedocs.org/en/latest/
