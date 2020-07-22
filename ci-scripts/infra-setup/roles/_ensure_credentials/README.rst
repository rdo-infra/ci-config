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
  - name: ensure credentials are created
    become: true
    become_user: "{{ promoter_user }}"
    include_role:
      name: _ensure_credentials
    vars:
      registry_secret_path: "{{ remote_path_registry_secret }}"
      dlrnapi_secret_path: "{{ remote_path_dlrnapi_secret }}"
      uploader_key_path: "{{ remote_path_uploader_key }}"
```
