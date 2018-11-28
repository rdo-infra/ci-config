ci-reproducer
===================

An Ansible role to start a CI zuul + gerrit environment to test jobs and
patches at an openstack tenant or a ready provisioned VMs like libvirt.

Requirements
------------

* [docker](https://docs.docker.com/install/)
* [openstack auth config at clouds.yaml](https://docs.openstack.org/python-openstackclient/pike/configuration/index.html)
* [centos-7 and fedora-28 images](https://nb02.openstack.org/images/)
* [virt-edit to inject pub keys to images](https://docs.openstack.org/image-guide/modify-images.html)
* Sudo permissions

Role Variables
--------------

* `os_cloud_name` -- openstack cloud to use, it has to be defined at
  clouds.yaml
* `os_centos7_image` -- Image to use at centos-7 nodesets,
  default value is penstack-infra-centos-7
* `os_fedora28_image` -- Image to use at fedora-28 nodesets,
  default value is penstack-infra-centos-7
* `upstream_gerrit_user` -- User clone repos from review.openstack.org,
* `rdo_gerrit_user` -- User clone repos from review.rdoproject.org,
  default value is ansible_user
* `install_path` -- Path to install reproducer, after installation
  is possible to play with docker-compose commands for more advanced uses,
  default is ansible_user_dir/tripleo-ci-reproducer/
* `state` -- Action to do 'present' to start 'absent' to stop.
* `build_zuul` and `build_nodepool` -- Point to a zuul/nodepool version to use
  with 'version' and 'refspec' example:
       build_zuul:
          version: FETCH_HEAD
          refspec: refs/changes/77/607077/1
       build_nodepool:
          version: HEAD
          refspec: refs/for/master


Example Playbook
----------------

```yaml
---
- name: Start reproducer
  hosts: virthost
  vars:
    state: present
  roles:
    - ci-reproducer
```

```yaml
---
- name: Stop reproducer
  hosts: virthost
  vars:
    state: absent
  roles:
    - ci-reproducer
```
License
-------

Apache

Author Information
------------------

Openstack Tripleo CI Team
