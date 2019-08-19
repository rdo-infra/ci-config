call get_latest_hashes
dlrn_hash = latest_hashes[0]
promote(dlrn_hash, "tripleo-ci-staging")


# STAted setup for containers
docker pull rdo-registry/staging/container1
docker pull rdo-registry/stating/container2
docker tag rdo-registry/staging/container1 rdo-registry/container/container1:dlrn_hash
docker tag rdo-registry/staging/container2 rdo-registry/container/container2:dlrn_hash
docker push rdo-registry/staging/container1:dlrn_hash
docker push rdo-registry/stating/container2:dlrn_hash

# staged setup for images

sftp ln -s staged-images /path/to/dlrn_hash
sftp ln -s staged-images /path/to/tripleo-ci-staging

# Staged job reports


dlrnapi_report("staging-job-1", "success")
dlrnapi_report("staging-job-2", "success")
