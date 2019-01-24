#!/bin/bash
# This can be used when we need some temporary quick fix for CI while we wait for the change
# to get merged upstream.
# We need it to happen before we get a node from cico so that the correct changes end up in
# the quickstart venv
set -eux

pushd $WORKSPACE/tripleo-quickstart
# Add git checkouts for tripleo-quickstart here
popd

pushd $WORKSPACE/tripleo-quickstart-extras
# Add git checkouts for tripleo-quickstart-extras here
popd

cp $WORKSPACE/tripleo-quickstart/requirements.txt $WORKSPACE/local-requires.txt
echo "file://$WORKSPACE/tripleo-quickstart-extras/#egg=tripleo-quickstart-extras" >> $WORKSPACE/local-requires.txt

bash $WORKSPACE/tripleo-quickstart/quickstart.sh \
    --working-dir $WORKSPACE/.quickstart \
    --no-clone \
    --clean \
    --bootstrap \
    --requirements $WORKSPACE/local-requires.txt \
    --playbook noop.yml \
    localhost
