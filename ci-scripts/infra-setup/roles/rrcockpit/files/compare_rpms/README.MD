**setup**
```
python3 -m venv {dir}
source {dir}/bin/activate
pip3 install -r requirements.txt
python3 setup.py install

#execute
diff_tripleo_builds --help

```

Usage: diff_builds.py [OPTIONS]

  This script takes two urls for ci log files and compares the rpms
  installed in each environment. We have named the first a control_url as in
  a control and experiment to display the diff.

  The script will pull rpms from ALL the nodes available, and the containers
  hosted on that node. This workds with both upstream tripleo jobs and
  infrared job logs.

  USAGE:     The script expects only the base url ( up to the logs dir ) of
  the logs from any job.     e.g.
  https://logserver.rdoproject.org/foo/check/jobs/7822e6c/logs/

Options:
  -c, --control_url TEXT     a url that points to list of rpms that are used
                             as the control in the diff  [required]

  -t, --test_url TEXT        a url that points to the rpms to be compared
                             against the control list  [required]

  -a, --all_available        Some jobs are not logging container rpms, use
                             output from repoquery instead

  -p, --package_ignore PATH  A file that enables some packages to be ignored
                             from the diff

  -q, --diff_compose         diff the metadata rpms.json from a compose
  -u, --undercloud_only      use the undercloud only, ignore the controller,
                             compute and ceph nodes

  --help                     Show this message and exit.
```

**Examples**
```
# Diff logs from CI
diff_tripleo_builds.py  -c https://storage.gra.cloud.ovh.net/v1/AUTH_dcaab5e32b234d56b626f72581e3644c/zuul_opendev_logs_a7d/756888/2/gate/tripleo-ci-centos-8-containers-multinode-train/a7d91e1/logs -t https://logserver.rdoproject.org/openstack-periodic-integration-stable2/opendev.org/openstack/tripleo-ci/master/periodic-tripleo-ci-centos-8-containers-multinode-train/b2de4cb/logs

# Diff logs from a Compose
diff_builds.py -q -c http://foo/RHOS-16.2-RHEL-8-20201015.n.1/compose -t http://foo/RHOS-16.2-RHEL-8-20201014.n.3/compose

```

**Example Ignore Package File**
```
zsh
zsh-html
zstd
```
**Example Ignore Package with Wild Cards**
```
zsh.*
foo
```

**Example Output**
```
+------------+---------------------------------------+-------------------------+----------------------+
|    Node    |              Package_Name             | Control Package Version | Test Package Version |
+------------+---------------------------------------+-------------------------+----------------------+
| undercloud |              libmodulemd              |      not installed      |        2.8.2         |
| undercloud |           openstack-heat-api          |          13.1.0         |        13.0.3        |
| undercloud |         openstack-heat-common         |          13.1.0         |        13.0.3        |
| undercloud |         openstack-heat-engine         |          13.1.0         |        13.0.3        |
| undercloud |        openstack-heat-monolith        |          13.1.0         |        13.0.3        |
| undercloud | openstack-ironic-python-agent-builder |          2.2.1          |        2.1.1         |
| undercloud |           openstack-neutron           |          15.3.1         |        15.2.1        |
| undercloud |        openstack-neutron-common       |          15.3.1         |        15.2.1        |
| undercloud |         openstack-neutron-ml2         |          15.3.1         |        15.2.1        |
| undercloud |     openstack-neutron-openvswitch     |          15.3.1         |        15.2.1        |
| undercloud |           openstack-tempest           |          25.0.0         |        24.0.0        |
| undercloud |            puppet-pacemaker           |          1.1.1          |        1.0.1         |
| undercloud |        python-oslo-privsep-lang       |          1.33.4         |        1.33.3        |
| undercloud |           python3-heatclient          |          1.18.1         |        1.18.0        |
| undercloud |            python3-neutron            |          15.3.1         |        15.2.1        |
| undercloud |          python3-oslo-privsep         |          1.33.4         |        1.33.3        |
| undercloud |            python3-tempest            |          25.0.0         |        24.0.0        |
| undercloud |        python3-validations-libs       |          1.0.5          |    not installed     |
| undercloud |           validations-common          |          1.1.2          |    not installed     |
+------------+---------------------------------------+-------------------------+----------------------+
+------------+--------------------------+-------------------------+----------------------+
|    Node    |       Package_Name       | Control Package Version | Test Package Version |
+------------+--------------------------+-------------------------+----------------------+
| controller |       libmodulemd        |      not installed      |        2.8.2         |
| controller |    openstack-heat-ui     |          2.0.2          |        2.0.1         |
| controller |    openstack-neutron     |          15.3.1         |        15.2.1        |
| controller | openstack-neutron-common |          15.3.1         |        15.2.1        |
| controller |  openstack-neutron-ml2   |          15.3.1         |        15.2.1        |
| controller |  platform-python-devel   |      not installed      |        3.6.8         |
| controller |     puppet-pacemaker     |          1.1.1          |        1.0.1         |
| controller | python-oslo-privsep-lang |          1.33.4         |        1.33.3        |
| controller |    python-rpm-macros     |      not installed      |          3           |
| controller |    python3-heatclient    |          1.18.1         |        1.18.0        |
| controller |     python3-neutron      |          15.3.1         |        15.2.1        |
| controller |   python3-oslo-privsep   |          1.33.4         |        1.33.3        |
| controller |  python3-rpm-generators  |      not installed      |          5           |
| controller |    python3-virtualenv    |      not installed      |        15.1.0        |
| controller |   python3-wheel-wheel    |      not installed      |        0.31.1        |
| controller |      python36-devel      |      not installed      |        3.6.8         |
+------------+--------------------------+-------------------------+----------------------+

```
