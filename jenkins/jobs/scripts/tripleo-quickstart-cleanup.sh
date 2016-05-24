# tripleo-quickstart-cleanup.sh
# A script to cleanup after tripleo-quickstart jobs
# Collects logs and returns the node
set -eux

pushd $WORKSPACE/tripleo-quickstart
infra_result=0
bash $WORKSPACE/tripleo-quickstart/ci-scripts/collect-logs.sh &> $WORKSPACE/collect_logs.txt || infra_result=1
bash $WORKSPACE/tripleo-quickstart/ci-scripts/return-node.sh &> $WORKSPACE/cleanup.txt || infra_result=2

if [[ "$infra_result" != "0" && "$result" = "0" ]]; then
  # if the job/test was ok, but collect_logs/cleanup failed,
  # print out why the collect_logs/cleanup failed
  cat $WORKSPACE/collect_logs.txt
  cat $WORKSPACE/cleanup.txt
fi
popd