Currently contains two script ruck_rover.py and promotion_status.py, will work on reorganizingto move to single script.


$ python3 ruck_rover.py --help
Usage: ruck_rover.py [OPTIONS]

Options:
  --release [master|wallaby|victoria|ussuri|train|osp17|osp16-2]
  --component [all|baremetal|cinder|clients|cloudops|common|compute|glance|manila|network|octavia|security|swift|tempest|tripleo|ui|validation]
  --influx
  --help                          Show this message and exit

Example:-

* To track integration line jobs:-

$ python3 find_jobs_in_criteria.py --release master
Hash under test: 40581968b0f8c1ce948af93abd7de182
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Jobs which passed:                                                               ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ periodic-tripleo-centos-8-buildimage-overcloud-full-master                       │
│ periodic-tripleo-ci-centos-8-standalone-master                                   │
│ periodic-tripleo-ci-centos-8-multinode-1ctlr-featureset037-updates-master        │
│ periodic-tripleo-centos-8-buildimage-ironic-python-agent-master                  │
│ periodic-tripleo-ci-centos-8-scenario012-standalone-master                       │
│ periodic-tripleo-ci-centos-8-scenario000-multinode-oooq-container-updates-master │
│ periodic-tripleo-centos-8-buildimage-overcloud-hardened-full-master              │
│ periodic-tripleo-ci-build-containers-ubi-8-push                                  │
│ periodic-tripleo-ci-centos-8-undercloud-containers-master                        │
│ periodic-tripleo-ci-centos-8-scenario002-standalone-master                       │
│ periodic-tripleo-ci-centos-8-scenario004-standalone-master                       │
│ periodic-tripleo-ci-centos-8-scenario007-standalone-master                       │
│ periodic-tripleo-ci-centos-8-scenario003-standalone-master                       │
│ periodic-tripleo-ci-centos-8-containers-undercloud-minion-master                 │
└──────────────────────────────────────────────────────────────────────────────────┘
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Jobs which failed:                                                               ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ periodic-tripleo-ci-centos-8-standalone-upgrade-master                           │
│ periodic-tripleo-ci-centos-8-scenario001-standalone-master                       │
└──────────────────────────────────────────────────────────────────────────────────┘
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Jobs whose results are awaited                                                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset035-master                │
│ periodic-tripleo-ci-centos-8-standalone-on-multinode-ipa-master                  │
│ periodic-tripleo-ci-centos-8-multinode-1ctlr-featureset030-master                │
│ periodic-tripleo-ci-centos-8-multinode-1ctlr-featureset010-master                │
│ periodic-tripleo-ci-centos-8-standalone-full-tempest-api-master                  │
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp_1supp-featureset039-master          │
│ periodic-tripleo-ci-centos-8-scenario010-ovn-provider-standalone-master          │
│ periodic-tripleo-ci-centos-8-ovb-1ctlr_1comp-featureset002-master                │
│ periodic-tripleo-ci-centos-8-ovb-1ctlr_2comp-featureset020-master                │
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-master                │
│ periodic-tripleo-ci-centos-8-standalone-full-tempest-scenario-master             │
└──────────────────────────────────────────────────────────────────────────────────┘
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Jobs which are in promotion criteria and need pass to promote the Hash:          ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset035-master                │
│ periodic-tripleo-ci-centos-8-standalone-on-multinode-ipa-master                  │
│ periodic-tripleo-ci-centos-8-multinode-1ctlr-featureset030-master                │
│ periodic-tripleo-ci-centos-8-multinode-1ctlr-featureset010-master                │
│ periodic-tripleo-ci-centos-8-standalone-full-tempest-api-master                  │
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp_1supp-featureset039-master          │
│ periodic-tripleo-ci-centos-8-scenario010-ovn-provider-standalone-master          │
│ periodic-tripleo-ci-centos-8-scenario001-standalone-master                       │
│ periodic-tripleo-ci-centos-8-ovb-1ctlr_1comp-featureset002-master                │
│ periodic-tripleo-ci-centos-8-ovb-1ctlr_2comp-featureset020-master                │
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-master                │
│ periodic-tripleo-ci-centos-8-standalone-full-tempest-scenario-master             │
└──────────────────────────────────────────────────────────────────────────────────┘
Logs of jobs which are failing:-
https://logserver.rdoproject.org/openstack-periodic-integration-main/opendev.org/openstack/tripleo-ci/master/periodic-tripleo-ci-centos-8-standalone-upgrade-m
aster/cd6d83b
https://logserver.rdoproject.org/openstack-periodic-integration-main/opendev.org/openstack/tripleo-ci/master/periodic-tripleo-ci-centos-8-scenario001-standalo
ne-master/da88098

* To track component line jobs

$ python3 ruck_rover.py --component all --release master
baremetal component, status=Yellow
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Jobs which failed:                                                               ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
└──────────────────────────────────────────────────────────────────────────────────┘
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Jobs whose results are awaited                                                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-baremetal-master      │
└──────────────────────────────────────────────────────────────────────────────────┘
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ baremetal component jobs which need pass to promote the hash:                    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-baremetal-master      │
└──────────────────────────────────────────────────────────────────────────────────┘


cinder component, status=Green


clients component, status=Red
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Jobs which failed:                                                               ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-clients-master        │
└──────────────────────────────────────────────────────────────────────────────────┘
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Jobs whose results are awaited                                                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
└──────────────────────────────────────────────────────────────────────────────────┘
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ clients component jobs which need pass to promote the hash:                      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
└──────────────────────────────────────────────────────────────────────────────────┘
Logs of failing jobs:
https://logserver.rdoproject.org/openstack-component-clients/opendev.org/openstack/tripleo-ci/master/periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-clients-master/4e54403

* The data this tool create will be picked by telegraf to populate influxdb to be consumed by grafana.

$ python3 ruck_rover.py --component baremetal --release wallaby --influx
missing_jobs,job_type=component release=wallaby,name=promoted-components,job_name=periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-baremetal-wallaby
,test_hash=fc8e1652b06336f91a268583f6606731e8715509_ae8cc88e,criteria=yes,logs=https://logserver.rdoproject.org/openstack-component-baremetal/opendev.org/open
stack/tripleo-ci/master/periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-baremetal-wallaby/01e16b2,component=baremetal

$ python3 promotion_status.py
centos8 based releases
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Release                        ┃ Days behind promotion          ┃ New content available?         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ master                         │ 7                              │ True                           │
│ wallaby                        │ 6                              │ True                           │
│ victoria                       │ 14                             │ True                           │
│ ussuri                         │ 9                              │ True                           │
│ train                          │ 4                              │ True                           │
└────────────────────────────────┴────────────────────────────────┴────────────────────────────────┘
centos7 based releases
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Release                        ┃ Days behind promotion          ┃ New content available?         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ train                          │ 26                             │ True                           │
│ stein                          │ 13                             │ True                           │
│ queens                         │ 16                             │ True                           │
└────────────────────────────────┴────────────────────────────────┴────────────────────────────────┘
rhel8 based releases
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Release                        ┃ Days behind promotion          ┃ New content available?         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ osp16-2                        │ 7                              │ True                           │
│ osp17                          │ 28                             │ True                           │
└────────────────────────────────┴────────────────────────────────┴────────────────────────────────┘
