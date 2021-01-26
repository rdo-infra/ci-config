import json
import unittest

import last_promotions


class TestLastPromotions(unittest.TestCase):

    def setUp(self):
        self.url = last_promotions.DEFAULT_PROMOTER_BASE_URL
        self.upstream_releases = [
            'master', 'victoria', 'ussuri', 'train']

    def test_get_last_promotion(self):
        for release in self.upstream_releases:
            args = {
                'url': self.url,
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
            result = json.dumps(result)
            self.assertIn("name=current-tripleo", result, msg=None)
            self.assertIn("name=current-tripleo-rdo", result, msg=None)

    def test_get_invalid_promotion(self):
        self.assertRaises(
            Exception, last_promotions.get_promotion,
            self.url, 'test_release', 'CentOS-8', None)
