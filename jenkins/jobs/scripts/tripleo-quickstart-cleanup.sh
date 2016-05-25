# tripleo-quickstart-cleanup.sh
# A script to cleanup after tripleo-quickstart jobs
# Collects logs and returns the node
set -eux

pushd $WORKSPACE/tripleo-quickstart

scripts_dir=$WORKSPACE/tripleo-quickstart/ci-scripts/
# We are only interested in output from the collect-logs script if it fails
bash $scripts_dir/collect-logs.sh &> $WORKSPACE/collect_logs.txt ||
     cat $WORKSPACE/collect_logs.txt
bash $scripts_dir/return-node.sh
popd