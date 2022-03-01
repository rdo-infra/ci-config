To prepare the environment for deployment:

    cd /tmp/
    git clone https://review.rdoproject.org/r/p/rdo-infra/ci-config.git
    virtualenv deploy
    source deploy/bin/activate
    pip install ansible shade
    cd ci-config/ci-scripts/infra-setup
    export ANSIBLE_ROLES_PATH=$PWD/roles
    source <cloud-credentials>
    cd tests
    ./full-run.sh

To tear down everything:

    ./nuke.sh
