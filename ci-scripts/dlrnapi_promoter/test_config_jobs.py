import os

import requests
import yaml

COMPONENT_JOBS_HOME = 'config'
CRITERIA_JOBS_HOME = 'config_environments/rdo'
EXCEPTION_JOBS = [
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-network-'
    'train',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-network-'
    'master',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-octavia-'
    'ussuri',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-octavia-'
    'wallaby',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-octavia-'
    'master',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-octavia-'
    'train',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-network-'
    'victoria',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-octavia-'
    'victoria',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-network-'
    'ussuri',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-network-'
    'wallaby',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-wallaby',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-train',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-master',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-ussuri',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-victoria',
    'periodic-tripleo-ci-centos-8-scenario010-kvm-internal-standalone-wallaby'
]  # noqa: E501


class ZuulAPI:
    def __init__(self, name, tenant='openstack'):
        self.name = name
        self.tenant = tenant

    def get_jobs(self):
        if self.tenant:
            url = os.path.join(self.name, 'api', 'tenant', self.tenant, 'jobs')
        else:
            url = os.path.join(self.name, 'api', 'jobs')
        jobs = requests.get(url)
        all_jobs = jobs.json()
        return [i['name'] for i in all_jobs]


class TestZuulAPI:

    def test_get_jobs(self):
        zuul_client = ZuulAPI('https://zuul.opendev.org')
        all_jobs = zuul_client.get_jobs()
        assert 'multinode' in all_jobs

    def test_get_jobs_rdo(self):
        zuul_client = ZuulAPI('https://review.rdoproject.org/zuul', tenant='')
        all_jobs = zuul_client.get_jobs()
        assert 'multinode' in all_jobs


class ConfigFiles:
    def __init__(self, component=True):
        self.component = component

    def get_files(self):
        """
        This method will return file list for the component and criteria
        """
        all_files = []
        jobs_home = COMPONENT_JOBS_HOME if self.component \
            else CRITERIA_JOBS_HOME
        for dirs, subdir, files in os.walk(os.path.join(os.curdir, jobs_home)):
            for f in files:
                if f in ['defaults.yaml', 'global_defaults.yaml']:
                    continue
                if f.endswith('.yaml'):
                    f_path = os.path.join(os.path.abspath(dirs), f)
                    if os.path.isfile(f_path):
                        all_files.append(f_path)
                    else:
                        raise FileNotFoundError
        return all_files

    def get_jobs_from_file(self, files):
        """
        This method will return jobs from component file.
        """
        jobs = []
        if isinstance(files, str):
            file_data = open(files).read()
            yaml_data = yaml.safe_load(file_data)
            if self.component:
                if 'promoted-components' in yaml_data.keys():
                    components = yaml_data['promoted-components']
                    for key, value in components.items():
                        if value:
                            jobs.extend(value)
            else:
                if 'criteria' in yaml_data[
                        'promotions']['current-tripleo'].keys():
                    criteria = yaml_data[
                        'promotions']['current-tripleo']['criteria']
                    if criteria:
                        jobs.extend(criteria)
        return jobs


class TestConfigFiles:
    def test_validate_component_jobs(self):
        config = ConfigFiles()
        zuul_client = ZuulAPI('https://review.rdoproject.org/zuul', tenant='')

        file_jobs = []

        c_files = config.get_files()
        for f in c_files:
            file_jobs.extend(config.get_jobs_from_file(f))
        all_jobs = zuul_client.get_jobs()
        common_jobs = set(file_jobs).intersection(all_jobs)
        file_jobs_without_exception = set(file_jobs) - set(EXCEPTION_JOBS)
        assert len(common_jobs) == len(file_jobs_without_exception)

    def test_validate_criteria_jobs(self):
        config = ConfigFiles(component=False)
        zuul_client = ZuulAPI("https://review.rdoproject.org/zuul", tenant='')

        file_jobs = []
        c_files = config.get_files()
        for f in c_files:
            file_jobs.extend(config.get_jobs_from_file(f))
        all_jobs = zuul_client.get_jobs()
        common_jobs = set(file_jobs).intersection(all_jobs)
        file_jobs_without_exception = set(file_jobs) - set(EXCEPTION_JOBS)
        assert len(common_jobs) == len(file_jobs_without_exception)
