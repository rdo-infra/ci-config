# push-quay.py

## Introduction

This script pull images from one registry and push to another one. Initially
is to be used with rdo registry and quay.io, but you can specify other 
registries.

## Installation

To install just install the requirements with pip:

```
pip install -r requirements
```

And then execute

## Requirements

The script requires podman > 2.1.0. Because this is the version of podman who
have the restapi enabled.

## Executing

There are several options, mostly of them with defaults, but the two required
are the `--username` and `--password`. The other options are listed below:


| Option            | Description | Defaults |
| --------          | -------- | -------- |
| `--zuul-api`      | Zuul endpoint api.     | https://review.rdoproject.org/zuul/api/ |
| `--pull-registry` | Registry url to pull images from | trunk.registry.rdoproject.org |
| `--push-registry` | Registry url to push images to | quay.io/tripleoci |
| `--release`       | Release name to pull/push images | tripleomaster |
| `--podman-uri`    | URI for podman | unix://localhost/run/user/1000/podman/podman.sock |
| `--job`           | Name of the job where zuul will collect the built containers | periodic-tripleo-ci-build-containers-ubi-8-push |
| `--image-tag`     | Image tag to be pulled | current-tripleo |
| `--prune`         | Remove all images from local before pull new ones | False |
| `--push`          | Push all images from local to `--push-registry` | False |
| `--pull`          | Pull all images from `--pull-registry` to local | False |
| `--username`      | Username to push images | |
| `--password`      | Password to push images. It should be the encrypted version | |
| `--container`     | If specified, the `--push`, `--pull` and `--prune` options will only be executed on that specific container name | |

## Example of usage:

You can use the push-quay script in may different ways:

### All in one
`push-quay.py --username user --password password --prune --pull --push`

This will delete all images locally, pull new ones and push. It doesn't matter
the order of the options, the execution order will always be delete, pull
and then push.

### Pull only

`push-quay.py --username user --password password pull`

### Other examples

`push-quay.py --username user --password password --release tripleomaster --zuul-api zuul.openstack.org/api --push-registry quay.io/tripleoci --release tripleomaster`
