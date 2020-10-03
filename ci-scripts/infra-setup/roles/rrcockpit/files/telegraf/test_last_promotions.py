import unittest

import last_promotions


class TestLastPromotions(unittest.TestCase):

    def setUp(self):
        self.internal_url = (
            'http://git.app.eng.bos.redhat.com/git/'
            'tripleo-environments.git/plain/'
        )
        self.redhat_releases = ['rhos-17', 'rhos-16.2']
        self.components = [
            'baremetal', 'cinder', 'clients', 'cloudops', 'common', 'compute',
            'glance', 'manila', 'network', 'octavia', 'security', 'swift',
            'tempest', 'tripleo', 'ui', 'validation'
        ]
        self.upstream_releases = [
            'master', 'ussuri', 'train', 'stein', 'rocky','queens'
        ]
        self.upstream_distributions = ['CentOS-8', 'CentOS-7']


    def test_last_promotions_with_redhat_8(self):

        for release in self.redhat_releases:
            for component in self.components:
                args = {
                    'url': self.internal_url,
                    'release': release,
                    'distro': 'RedHat-8',
                    'component': component
                }

                result = last_promotions.get_promotion(
                    args['url'],
                    args['release'],
                    args['distro'],
                    args['component']
                )

    def test_last_promotions_with_redhat_8_without_components(self):
        for release in self.redhat_releases:
            args = {
                'url': self.internal_url,
                'release': release,
                'distro': 'RedHat-8',
                'component': None
            }

            result = last_promotions.get_promotion(
                args['url'],
                args['release'],
                args['distro'],
                args['component']
            )

    def test_last_promotion_with_centos_8(self):
        for release in ['master', 'ussuri', 'train']:
            for component in self.components:
                args = {
                    'url': last_promotions.DEFAULT_PROMOTER_BASE_URL,
                    'release': release,
                    'distro': 'CentOS-8',
                    'component': component
                }

                result = last_promotions.get_promotion(
                    args['url'],
                    args['release'],
                    args['distro'],
                    args['component']
                )

    def test_last_promotion_with_centos_8_without_components(self):
        for release in ['master', 'ussuri', 'train']:
            args = {
                'url': last_promotions.DEFAULT_PROMOTER_BASE_URL,
                'release': release,
                'distro': 'CentOS-8',
                'component': None
            }

            result = last_promotions.get_promotion(
                args['url'],
                args['release'],
                args['distro'],
                args['component']
            )

    def test_last_promotion_with_centos_7_without_components(self):
        for release in ['train', 'stein', 'rocky', 'queens']:
            args = {
                'url': last_promotions.DEFAULT_PROMOTER_BASE_URL,
                'release': release,
                'distro': 'CentOS-7',
                'component': None
            }

            result = last_promotions.get_promotion(
                args['url'],
                args['release'],
                args['distro'],
                args['component']
            )
