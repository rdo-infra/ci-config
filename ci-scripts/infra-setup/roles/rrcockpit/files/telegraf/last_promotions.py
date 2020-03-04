#!/usr/bin/env python

import argparse
import dlrnapi_client

from influxdb_utils import format_ts_from_float
from promoter_utils import get_dlrn_instance
from promoter_utils import get_promoter_config
from promoter_utils import get_promoter_component_config

PROMOTION_INFLUXDB_LINE = ("dlrn-promotion,"
                           "release={release},distro={distro},"
                           "name={promote_name} "
                           "commit_hash=\"{commit_hash}\","
                           "distro_hash=\"{distro_hash}\","
                           "repo_hash=\"{repo_hash}\","
                           "repo_url=\"{repo_url}\","
                           "component=\"{component}\","
                           "{timestamp}")


def influxdb(promotion):
    promotion['timestamp'] = format_ts_from_float(promotion['timestamp'])
    return PROMOTION_INFLUXDB_LINE.format(**promotion)


def get_last_promotion(dlrn, release, distro, name, component=None):
    query = dlrnapi_client.PromotionQuery()
    query.promote_name = name
    if component:
        query.component = component
    promotions = dlrn.api_promotions_get(query)
    if promotions:
        last_promotion = promotions[0].to_dict()
        last_promotion['release'] = release
        last_promotion['distro'] = distro
        return last_promotion
    return


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Print release last promotions as influxdb lines")

    parser.add_argument('--release', required=True)
    parser.add_argument('--distro', default="CentOS-7")
    parser.add_argument('--component', default=None)
    args = parser.parse_args()

    if args.component is None:
        promoter_config = get_promoter_config(args.release, args.distro)
    else:
        promoter_config = get_promoter_component_config(
            args.release, args.distro)
    dlrn = get_dlrn_instance(promoter_config)
    if dlrn:
        for promotion_name in promoter_config['promote_from']:
            if args.component is None:
                promo = get_last_promotion(dlrn, args.release, args.distro,
                                           promotion_name)
            else:
                promo = get_last_promotion(dlrn, args.release, args.distro,
                                           promotion_name, args.component)
            if promo:
                print(influxdb(promo))
