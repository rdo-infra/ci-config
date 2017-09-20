Promoter Server Setup Scripts
=============================

This directory contains the ansible playbook used to setup the promoter-server
in the rdocloud environment.

To run, first fill out the proper passwords in `secrets.yml`, then:

    virtualenv /tmp/promoter-setup
    source /tmp/promoter-setup/bin/activate
    pip install -r requirements.txt
    ansible-playbook -v promoter-setup.yml -e @secrets.yml
