import os
import subprocess
import sys

from . import validate_config_jobs  # pylint: disable = E0402

print_error = validate_config_jobs.print_error
ZuulAPI = validate_config_jobs.ZuulAPI
ConfigFiles = validate_config_jobs.ConfigFiles

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

git_root_cmd = 'git rev-parse --show-toplevel'
try:
    ci_config_root = subprocess.check_output(git_root_cmd.split())
    ci_config_root = ci_config_root.decode().strip()
except subprocess.CalledProcessError:
    print_error("ERROR: Unable to get git root dir, using %s", git_root_cmd)
    sys.exit(1)

COMPONENT_JOBS_HOME = os.path.join(
    ci_config_root,
    'ci-scripts/dlrnapi_promoter/config')
INTEGRATION_JOBS_HOME = os.path.join(
    ci_config_root,
    'ci-scripts/dlrnapi_promoter/config_environments/rdo')


class TestZuulAPI:

    def test_get_jobs(self):
        zuul_client = ZuulAPI('https://zuul.opendev.org')
        all_jobs = zuul_client.get_jobs()
        assert 'multinode' in all_jobs

    def test_get_jobs_rdo(self):
        zuul_client = ZuulAPI('https://review.rdoproject.org/zuul', tenant='')
        all_jobs = zuul_client.get_jobs()
        assert 'multinode' in all_jobs


class TestConfigFiles:
    def setup_method(self):
        self.zuul_url = 'https://review.rdoproject.org/' \
                        'zuul'  # pylint: disable = W0201
        self.tenant = ''  # pylint: disable = W0201

    def test_validate_component_jobs(self):
        config = ConfigFiles(config_dir=COMPONENT_JOBS_HOME)
        zuul_client = ZuulAPI(self.zuul_url, tenant=self.tenant)

        file_jobs = []

        c_files = config.get_files()
        for f in c_files:
            file_jobs.extend(config.get_jobs_from_file(f))
        all_jobs = zuul_client.get_jobs()
        common_jobs = set(file_jobs).intersection(all_jobs)
        file_jobs_without_exception = set(file_jobs) - set(EXCEPTION_JOBS)
        assert (len(common_jobs) > 1) == (len(file_jobs_without_exception) > 1)

    def test_validate_criteria_jobs(self):
        config = ConfigFiles(config_dir=INTEGRATION_JOBS_HOME)
        zuul_client = ZuulAPI(self.zuul_url, tenant=self.tenant)

        file_jobs = []
        c_files = config.get_files()
        for f in c_files:
            file_jobs.extend(config.get_jobs_from_file(f))
        all_jobs = zuul_client.get_jobs()
        common_jobs = set(file_jobs).intersection(all_jobs)
        file_jobs_without_exception = set(file_jobs) - set(EXCEPTION_JOBS)
        assert (len(common_jobs) > 1) == (len(file_jobs_without_exception) > 1)
