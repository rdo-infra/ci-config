import docker

generate name

docker pull rdo-registry/staging/container1
docker pull rdo-registry/stating/container2
docker tag rdo-registry/staging/container1 rdo-registry/container/container1:dlrn_hash
docker tag rdo-registry/staging/container2 rdo-registry/container/container2:dlrn_hash
docker push rdo-registry/staging/container1:dlrn_hash
docker push rdo-registry/stating/container2:dlrn_hash

