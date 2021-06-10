Currently contains two script ruck_rover.py and promotion_status.py, will work on reorganizingto move to single script.


$ python3 ruck_rover.py --help
Usage: ruck_rover.py [OPTIONS]

Options:
  --release [master|wallaby|victoria|ussuri|train|osp17|osp16-2]
  --help                          Show this message and exit.

Example:-

$ python3 find_jobs_in_criteria.py --release master
Hash under test: 7699b331c84cb6d0942d5cf2c13e0e1e
passed:

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Job name                                                                         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ periodic-tripleo-ci-centos-8-standalone-master                                   │
│ periodic-tripleo-ci-centos-8-multinode-1ctlr-featureset030-master                │
│ periodic-tripleo-ci-centos-8-scenario001-standalone-master                       │
│ periodic-tripleo-centos-8-buildimage-overcloud-full-master                       │
│ tripleo-upstream-containers-build-master-ppc64le                                 │
│ periodic-tripleo-ci-centos-8-undercloud-upgrade-master                           │
│ periodic-tripleo-ci-centos-8-scenario004-standalone-master                       │
│ periodic-tripleo-ci-centos-8-scenario012-standalone-master                       │
│ periodic-tripleo-ci-centos-8-multinode-1ctlr-featureset037-updates-master        │
│ periodic-tripleo-ci-centos-8-scenario007-standalone-master                       │
│ periodic-tripleo-ci-centos-8-scenario000-multinode-oooq-container-updates-master │
│ periodic-tripleo-centos-8-buildimage-ironic-python-agent-master                  │
│ periodic-tripleo-ci-centos-8-scenario002-standalone-master                       │
│ periodic-tripleo-ci-centos-8-scenario003-standalone-master                       │
│ periodic-tripleo-ci-centos-8-standalone-upgrade-master                           │
│ periodic-tripleo-ci-centos-8-undercloud-containers-master                        │
│ periodic-tripleo-ci-build-containers-ubi-8-push                                  │
│ periodic-tripleo-ci-centos-8-standalone-on-multinode-ipa-master                  │
│ periodic-tripleo-ci-centos-8-containers-undercloud-minion-master                 │
│ periodic-tripleo-ci-centos-8-standalone-full-tempest-api-master                  │
│ periodic-tripleo-ci-centos-8-standalone-full-tempest-scenario-master             │
│ periodic-tripleo-centos-8-buildimage-overcloud-hardened-full-master              │
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset035-master                │
│ periodic-tripleo-ci-centos-8-multinode-1ctlr-featureset010-master                │
└──────────────────────────────────────────────────────────────────────────────────┘
Job which failed:

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Job name                                                                         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ periodic-tripleo-ci-centos-8-scenario010-standalone-master                       │
│ tripleo-podman-integration-centos-8-standalone                                   │
│ periodic-tripleo-ci-centos-8-scenario010-ovn-provider-standalone-master          │
│ periodic-tripleo-ci-centos-8-ovb-1ctlr_1comp-featureset002-master                │
│ periodic-tripleo-ci-centos-8-ovb-1ctlr_2comp-featureset020-master                │
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-master                │
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp_1supp-featureset039-master          │
│ periodic-tripleo-ci-centos-8-scenario010-kvm-standalone-master                   │
└──────────────────────────────────────────────────────────────────────────────────┘
Jobs with no result in dlrn:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Job name                                                                         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
└──────────────────────────────────────────────────────────────────────────────────┘
Jobs which are in promotion and need pass to promote:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Job name                                                                         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ periodic-tripleo-ci-centos-8-scenario010-standalone-master                       │
│ periodic-tripleo-ci-centos-8-scenario010-ovn-provider-standalone-master          │
│ periodic-tripleo-ci-centos-8-ovb-1ctlr_1comp-featureset002-master                │
│ periodic-tripleo-ci-centos-8-ovb-1ctlr_2comp-featureset020-master                │
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-master                │
│ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp_1supp-featureset039-master          │
└──────────────────────────────────────────────────────────────────────────────────┘

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
