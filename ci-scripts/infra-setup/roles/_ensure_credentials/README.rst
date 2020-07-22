_ensure_credentials
===================

Creates credentials for testing promoter services.
These credentials can be used across molecule scenarios and
zuul jobs.

Credentials:
  - container registry
  - image server
  - dlrnapi

Example:
```
  include_role: _ensure_credentials
  vars:
    registry_secret_path: "{{ remote_registry_secret_path }}"
    dlrnapi_secret_path: "{{ remote_dlrnapi_secret_path }}"
    uploader_key_path: "{{ remote_uploader_key_path }}"
  become: true
  become_user: "{{ promoter_user }}"
```
