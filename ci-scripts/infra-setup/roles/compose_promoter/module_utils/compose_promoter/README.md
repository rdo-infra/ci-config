# Compose Promoter

Compose Promoter is a tool for promoting Centos Compose-ID
as an artifact and store it in a remote server. This artifact
can be later consumed by continuous integration jobs to configure
their repos based on Centos Composes labels.

## Promotions

The current supported promotion is `latest-compose` which
promotes the latest available compose-id to `tripleo-ci-testing`.
