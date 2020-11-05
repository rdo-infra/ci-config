
# update the rpm skip list
cat /tmp/test  | grep "not available" | awk -F '|' '{ print $3, $5 }' | grep "not available" | awk '{ print $1 }'
