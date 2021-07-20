# Compose Promoter 

Compose Promoter is a tool for promoting Centos Compose-ID
as an artifact and store it in a remote server. This artifact
can be consumed by continuous integration jobs to configure
their repos based on Centos Composes.

## Configuration File

The `compose-promoter` supports yaml as configuration file to
provide the necessary info to promote compose:
  ```yaml
  server_hostname: "1.2.3.4"
  server_user: "user"
  server_port: 12345
  server_private_key_path: "~/.ssh/id_rsa"
  server_destination_dir: "/tmp"
  ```

## Promotions

The current supported promotion is `latest-compose` which 
promotes the latest available compose-id to `tripleo-ci-testing`.

```shell
 python3 compose_promoter.py latest-compose
```