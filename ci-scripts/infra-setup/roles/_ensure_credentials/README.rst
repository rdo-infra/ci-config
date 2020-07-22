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
  - name: Ensure credentials are created
    include_role:
      name: _ensure_credentials
    vars:
      ansible_become_user: "{{ promoter_user }}" # optional
```
