import unittest

import zuulv3_job_builds


class TestZuulV3JobBuilds(unittest.TestCase):

    def setUp(self):
        self.internal_url = (
            'http://zuul.openstack.org/api/'
        )
        self.type = 'upstream'
        self.pages = 1
        self.offset = 0

    def test_zuul_v3_job_builds_influx(self):
        expected = ('
                build,
                type=upstream,
                pipeline=check,
                branch=stable/rocky,
                project=openstack/puppet-tripleo,
                job_name=puppet-openstack-unit-4.8-centos-7,
                voting=True,change=737722,
                patchset=1,
                passed=True,
                cloud=null,
                region=null,
                provider=null,
                result="SUCCESS" 
                result="SUCCESS",
                result_num=1,
                log_url="https://4b0fd3e48caf1007a0de-4ded509a5d03b9dbe2159e2443546158.ssl.cf5.rackcdn.com/737722/1/check/puppet-openstack-unit-4.8-centos-7/105fa7b/",
                log_link="<a href=https://4b0fd3e48caf1007a0de-4ded509a5d03b9dbe2159e2443546158.ssl.cf5.rackcdn.com/737722/1/check/puppet-openstack-unit-4.8-centos-7/105fa7b/ target=\'_blank\'>puppet-openstack-unit-4.8-centos-7</a>",
                duration=2249.0,
                start=1603071617,
                end=1603073866,
                cloud="null",
                region="null",
                provider="null",
                sova_reason="",
                sova_tag="",
                container_prep_time_u=0 1603073866000000000' )

        obtained = zuulv3_job_builds.print_influx(
            self.type,
            get_builds_info(
                url=self.url,
                query={'project': 'openstack/puppet-tripleo'},
                pages=self.pages,
                offset=self.offset))

        assert (expected == obtained)

