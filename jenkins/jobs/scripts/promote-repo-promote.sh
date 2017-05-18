export PROMOTE_HASH=`echo $delorean_current_hash | awk -F '/' '{ print $3}'`

# Promote on the internal server and on the public, passive, one as well
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i ~/.ssh/rhos-ci -p 3300 promoter@$DELOREAN_HOST "sudo /usr/local/bin/promote.sh $PROMOTE_HASH" $RDO_VERSION $LINKNAME
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i ~/.ssh/rhos-ci -p 3300 promoter@$DELOREAN_PUBLIC_HOST "sudo /usr/local/bin/promote.sh $PROMOTE_HASH" $RDO_VERSION $LINKNAME
curl --max-time 60 http://rdo-feeder.distributed-ci.io/?RDO_VERSION=$RDO_VERSION || true
