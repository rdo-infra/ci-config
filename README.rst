ci-config
=========
Repository for Jenkins and general CI configuration for RDO.

To use it:

    pip install jenkins-job-builder

Create your ``config.ini`` from the ``config.ini.sample`` file, according to
your Jenkins configuration, then create/update the jobs, a bit like this::

    git clone https://github.com/rdo-infra/ci-config.git
    cd jenkins
    cp config.ini.sample config.ini
    # Edit config.ini to use your jenkins instance and credentials
    vi config.ini
    jenkins-jobs --conf config.ini update jobs

