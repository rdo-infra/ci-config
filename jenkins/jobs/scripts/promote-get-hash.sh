export HASH=`curl $DELOREAN_URL | grep baseurl | awk -F '/' '{ print $5"/"$6"/"$7 }'`

echo "delorean_current_hash = $HASH" > $HASH_FILE