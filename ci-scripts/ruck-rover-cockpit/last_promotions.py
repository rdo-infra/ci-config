#!/bin/env python

import requests
import ConfigParser
import dlrnapi_client
import argparse

from influxdb_utils import format_ts_from_float
from StringIO import StringIO


PROMOTER_CONFIG_URL=("https://raw.githubusercontent.com/rdo-infra/ci-config/"
                     "master/ci-scripts/dlrnapi_promoter/config/{}.ini")

PROMOTION_INFLUXDB_LINE=("dlrn-promotion,"
                          "release={release},name={promote_name} "
                          "commit_hash=\"{commit_hash}\","
                          "distro_hash=\"{distro_hash}\","
                          "repo_hash=\"{repo_hash}\","
                          "repo_url=\"{repo_url}\" "
                          "{timestamp}")

{'commit_hash': 'fdf5145eb6eb60372a093680968e9b9c322e13c6',
 'distro_hash': 'e82c0e4725b37eefb1e0c6ea475e11d87adf069b',
  'promote_name': 'current-tripleo',
   'repo_hash': 'fdf5145eb6eb60372a093680968e9b9c322e13c6_e82c0e47',
    'repo_url': 'https://trunk.rdoproject.org/centos7/fd/f5/fdf5145eb6eb60372a093680968e9b9c322e13c6_e82c0e47',
     'timestamp': 1527742419,
      'user': 'ciuser'}


def influxdb(promotion):
    promotion['timestamp'] = format_ts_from_float(promotion['timestamp'])
    return PROMOTION_INFLUXDB_LINE.format(**promotion)

def get_last_promotion(api_instance, release, name):
    query = dlrnapi_client.PromotionQuery()
    query.promote_name = name
    promotions = api_instance.api_promotions_get(query)
    last_promotion = promotions[0].to_dict()
    print(last_promotion)
    last_promotion['release'] = release
    return last_promotion

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Pring release last promotions as influxdb lines")

    parser.add_argument('--release', required=True)
    args = parser.parse_args()

    response = requests.get(
            PROMOTER_CONFIG_URL.format(args.release))
    if response.ok:
        config = ConfigParser.SafeConfigParser(allow_no_value=True)
        config.readfp(StringIO(response.content))

        api_client = dlrnapi_client.ApiClient(
                host=config.get('main', 'api_url'))
        api_instance = dlrnapi_client.DefaultApi(api_client=api_client)

        for promotion_name, _ in config.items('promote_from'):
            print(influxdb(get_last_promotion(
                    api_instance, args.release, promotion_name)))

