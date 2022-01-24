
FILE_STORAGE = "/tmp/logscache/"
LOG_FILE = "comparator.log"
DATA = {
    'oooq': 'ara.json',
    'undercloud': 'ara.oooq.root.json',
    'overcloud': 'ara.oooq.oc.json'
}

SQLITE_FILES = {
    'oooq': 'non-exist',
    'undercloud': 'ara_oooq_root/ara-report/ansible.sqlite',
    'overcloud': 'ara_oooq_overcloud/ara-report/ansible.sqlite'
}
RPM_LOC = 'undercloud/var/log/extra/rpm-list.txt'
PIP_LOC = 'undercloud/var/log/extra/pip.txt'
NAME_TO_PROJECT = {
    # Openstack packages
    'openstack-tripleo-common': 'openstack/tripleo-common',
    'python2-tripleo-common': 'openstack/tripleo-common',
    'openstack-tripleo-common-containers': 'openstack/tripleo-common',
    'openstack-tripleo-heat-templates': 'openstack/tripleo-heat-templates',
    'openstack-heat-api': 'openstack/heat',
    'openstack-heat-monolith': 'openstack/heat',
    'openstack-heat-common': 'openstack/heat',
    'openstack-heat-engine': 'openstack/heat',
    'ansible-role-tripleo-modify-image': (
        'openstack/ansible-role-tripleo-modify-image'),
    'openstack-tripleo-image-elements': 'openstack/tripleo-image-elements',
    'openstack-tripleo-validations': 'openstack/tripleo-validations',
    'tripleo-ansible': 'openstack/tripleo-ansible',
    'diskimage-builder': 'openstack/diskimage-builder',
    'paunch-services': 'openstack/paunch',
    'python2-paunch': 'openstack/paunch',
    'python3-paunch': 'openstack/paunch',
    'ironic-python-agent-builder': 'openstack/ironic-python-agent-builder',
    'python3-neutron-lib': 'openstack/neutron-lib',
    'python-neutron-lib': 'openstack/neutron-lib',
    'openstack-tempest': 'openstack/tempest',
    'python3-tempest': 'openstack/tempest',
    'python-tempest': 'openstack/tempest',
    # Openstack puppet modules
    'puppet-aodh': 'openstack/puppet-aodh',
    'puppet-barbican': 'openstack/puppet-barbican',
    'puppet-ceilometer': 'openstack/puppet-ceilometer',
    'puppet-ceph': 'openstack/puppet-ceph',
    'puppet-cinder': 'openstack/puppet-cinder',
    'puppet-concat': 'openstack/puppet-concat',
    'puppet-congress': 'openstack/puppet-congress',
    'puppet-corosync': 'openstack/puppet-corosync',
    'puppet-designate': 'openstack/puppet-designate',
    'puppet-ec2api': 'openstack/puppet-ec2api',
    'puppet-glance': 'openstack/puppet-glance',
    'puppet-gnocchi': 'openstack/puppet-gnocchi',
    'puppet-heat': 'openstack/puppet-heat',
    'puppet-horizon': 'openstack/puppet-horizon',
    'puppet-ironic': 'openstack/puppet-ironic',
    'puppet-keystone': 'openstack/puppet-keystone',
    'puppet-manila': 'openstack/puppet-manila',
    'puppet-mistral': 'openstack/puppet-mistral',
    'puppet-neutron': 'openstack/puppet-neutron',
    'puppet-nova': 'openstack/puppet-nova',
    'puppet-octavia': 'openstack/puppet-octavia',
    'puppet-openstack_extras': 'openstack/puppet-openstack_extras',
    'puppet-openstacklib': 'openstack/puppet-openstacklib',
    'puppet-oslo': 'openstack/puppet-oslo',
    'puppet-ovn': 'openstack/puppet-ovn',
    'puppet-pacemaker': 'openstack/puppet-pacemaker',
    'puppet-panko': 'openstack/puppet-panko',
    'puppet-placement': 'openstack/puppet-placement',
    'puppet-qdr': 'openstack/puppet-qdr',
    'puppet-sahara': 'openstack/puppet-sahara',
    'puppet-swift': 'openstack/puppet-swift',
    'puppet-tacker': 'openstack/puppet-tacker',
    'puppet-tripleo': 'openstack/puppet-tripleo',
    'puppet-trove': 'openstack/puppet-trove',
    'puppet-vswitch': 'openstack/puppet-vswitch',
    'puppet-zaqar': 'openstack/puppet-zaqar',
    # Puppet modules
    'puppet-apache': 'puppetlabs/puppetlabs-apache',
    'puppet-firewall': 'puppetlabs/puppetlabs-firewall',
    'puppet-haproxy': 'puppetlabs/puppetlabs-haproxy',
    'puppet-java': 'puppetlabs/puppetlabs-java',
    'puppet-stdlib': 'puppetlabs/puppetlabs-stdlib',
    'puppet-tomcat': 'puppetlabs/puppetlabs-tomcat',
    'puppet-vcsrepo': 'puppetlabs/puppetlabs-vcsrepo',
    'puppet-certmonger': 'saltedsignal/puppet-certmonger',
    # Related packages
    'buildah': 'containers/buildah',
    'ansible-role-lunasa-hsm': 'openstack/ansible-role-lunasa-hsm',
}
