# Arfiact Promoter

Artifact Promoter is a tool to be used for promoting generic
file artifacts, from a candidate to a target label.
The tool supports two type of promotions:

## Generic Artifact Promotion
The generic artifact promotion accepts any generic file promotion,
by providing the expected file name and content to be create in the
remote server.

### Promotions
Generic artifact promotion accepts any target label, and doesn't
need a candidate label for promotion.

## Compose Promoter
Promotes Centos Compose-ID as an artifact and store it in a remote
server. This artifact can be later consumed by continuous
integration jobs to configure their repos based on Centos
Composes labels.

### Promotions
CentOS Compose currently supports promotion from `latest-compose`, which
promotes the latest available compose-id to `centos-ci-testing`.
