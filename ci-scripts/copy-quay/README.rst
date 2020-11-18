Copy-quay
=========

This is a tool to copy containers from one registry to quay.

The functionality is as follow:

* Parse the containers-build job result
* Collect the containers built in the job
* Pull it from the source registry
* If it is a new container, create the repository as public in quay
* Push it to quay
* Tag the container with both current-tripleo and build id

Building
--------

Just run:

    $ go build -o copy-quay main.go copy.go utils.go quayapi.go

An executable copy-quay will be created

Usage
-----
Since this uses the podman api to copy the repositories, you can use podman to authenticate::

    $ podman login quay.io

Then, the simplest way to run it is::

    copy-quay --token $TOKEN --from-namespace tripleomaster --to-namespace tripleomaster copy

If you require to parse a job::

    copy-quay --token $TOKEN --from-namespace tripleoussuri --to-namespace tripleoussuri \
              --job periodic-tripleo-ci-build-containers-ubi-8-push-ussuri copy

Copying only one single container, for example from another registry::

    copy-quay --debug --pull-registry quay.ceph.io --token $TOKEN \
              --from-namespace ceph-ci --to-namespace ceph-ci \
              --tag v4.0.13-stable-4.0-nautilus-centos-7-x86_64 copy daemon

In the example above, it will copy the daemon tagged with v4.0.13-stable-4.0-nautilus-centos-7-x86_64 container
from quay.ceph.io and push it to quay.io/ceph-ci
