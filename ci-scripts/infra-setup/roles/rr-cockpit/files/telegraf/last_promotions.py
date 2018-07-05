#!/usr/bin/env python

import requests
import ConfigParser
import argparse
import dlrnapi_client

from influxdb_utils import format_ts_from_float
from promoter_utils import get_dlrn_instance
from promoter_utils import get_promoter_config
from StringIO import StringIO


PROMOTION_INFLUXDB_LINE=("dlrn-promotion,"
                          "release={release},name={promote_name} "
                          "commit_hash=\"{commit_hash}\","
                          "distro_hash=\"{distro_hash}\","
                          "repo_hash=\"{repo_hash}\","
                          "repo_url=\"{repo_url}\" "
                          "{timestamp}")

def influxdb(promotion):
    promotion['timestamp'] = format_ts_from_float(promotion['timestamp'])
    return PROMOTION_INFLUXDB_LINE.format(**promotion)

def get_last_promotion(dlrn, release, name):
    query = dlrnapi_client.PromotionQuery()
    query.promote_name = name
    promotions = dlrn.api_promotions_get(query)
    last_promotion = promotions[0].to_dict()
    last_promotion['release'] = release
    return last_promotion

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Pring release last promotions as influxdb lines")

    parser.add_argument('--release', required=True)
    args = parser.parse_args()

    promoter_config = get_promoter_config(args.release)
    dlrn = get_dlrn_instance(promoter_config)
    if dlrn:
        for promotion_name, _ in promoter_config.items('promote_from'):
            print(influxdb(get_last_promotion(
                    dlrn, args.release, promotion_name)))

