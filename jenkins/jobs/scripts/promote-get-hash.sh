new_hash=$(get_trunk_repository_hash $DELOREAN_URL)
old_hash=$(get_trunk_repository_hash $LAST_PROMOTED_URL)

# No need to run the whole promote pipeline if there is nothing new to promote
if [ $old_hash == $new_hash ]; then
    exit 23
fi

echo "delorean_current_hash = $new_hash" > $HASH_FILE