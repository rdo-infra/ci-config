#!/usr/bin/env python
# pylint: disable=C0413

import json
import os
import sys
import unittest

import yaml

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import last_promotions  # noqa


class Promotion(object):
    def __init__(self, promo):
        self.promo = promo

    def to_dict(self):
        return self.promo


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
                row = json.loads(line)
                all_master_promo.append(row)
            f.close()
        self.all_master_promo = all_master_promo

    def test_latest_promotion(self):
        # it seems dlrn always returns the very latest promotion
        # first, but probably good to verify that.
        # It's also probably worth while to have a non-voting
        # integration job that tests the live service
        promos_with_date = {}
        imported_promos = self.all_master_promo
        for i in imported_promos:
            if i['aggregate_hash']:
                promos_with_date[i['timestamp']] = i
        latest_promo = max(list(promos_with_date.keys()))
        self.assertEqual(latest_promo, imported_promos[0]['timestamp'])

    def test_get_dlrn_promotions(self):
        imported_promos = self.all_master_promo
        promos = []
        promos.append(Promotion(imported_promos[0]))
        promos.append(Promotion(imported_promos[1]))
        promo = last_promotions.get_last_promotion(promos,
                                                   "foo",
                                                   "bar")

        self.assertEquals(
                          promo['commit_hash'],
                          '02809ef4ec6112adb2bd960cb830503dab9a4c2a'
                         )
        self.assertEquals(promo['release'], "foo")
        self.assertEquals(promo['distro'], "bar")

    def test_update_promotion(self):
        imported_promos = self.all_master_promo
        promos = []
        promos.append(Promotion(imported_promos[0]))
        promos.append(Promotion(imported_promos[1]))
        promo = last_promotions.get_last_promotion(promos,
                                                   "foo",
                                                   "bar")

        consistent = 12345
        promotion_details = "http://promotion_details/foo"

        promo = last_promotions.update_promotion(promo,
                                                 promotion_details,
                                                 consistent)
        self.assertEquals(promo['promotion_details'], promotion_details)
        self.assertEquals(promo['consistent_date'], consistent)
