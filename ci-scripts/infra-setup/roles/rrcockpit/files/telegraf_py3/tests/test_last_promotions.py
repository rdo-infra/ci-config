#!/usr/bin/env python
# pylint: disable=C0413

import json
import os
import sys
import unittest
import yaml

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import last_promotions  # noqa


class TestLastPromotions(unittest.TestCase):

    def setUp(self):
        all_master_promo = []
        full_path = os.path.dirname(os.path.abspath(__file__))
        master_agg_path = '/data/aggregate_master_promo.yaml'
        self.url = last_promotions.DEFAULT_PROMOTER_BASE_URL
        self.upstream_releases = [
            'master', 'victoria', 'ussuri', 'train']
        with open(full_path + master_agg_path, 'r') as stream:
            self.master_agg = yaml.safe_load(stream)
        with open(full_path + '/data/all_master_promo', 'r') as f:
            for line in f:
                l = json.loads(f.readline())
                all_master_promo.append(l)
                print(all_master_promo)
            f.close()
        self.all_master_promo = all_master_promo



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
