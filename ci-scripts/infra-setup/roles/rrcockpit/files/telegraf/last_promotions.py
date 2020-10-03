#!/usr/bin/env python

import argparse
from datetime import datetime

import dlrnapi_client
import promoter_utils
from influxdb_utils import (format_ts_from_date, format_ts_from_float,
                            format_ts_from_last_modified)

PROMOTION_INFLUXDB_LINE = ("dlrn-promotion,"
                           "release={release},distro={distro},"
                           "name={promote_name} "
                           "commit_hash=\"{commit_hash}\","
                           "distro_hash=\"{distro_hash}\","
                           "repo_hash=\"{repo_hash}\","
                           "repo_url=\"{repo_url}\","
                           "consistent_date={consistent_date},"
                           "promotion_details=\"{promotion_details}\","
                           "component=\"{component}\" "
                           "{timestamp}")

DEFAULT_PROMOTER_BASE_URL = (
    "https://raw.githubusercontent.com/rdo-infra/ci-config/master"
)

def influxdb(promotion):
    promotion['timestamp'] = format_ts_from_float(promotion['timestamp'])
    return PROMOTION_INFLUXDB_LINE.format(**promotion)


def get_last_promotion(dlrn_client, release, distro, name, component=None):
    query = dlrnapi_client.PromotionQuery()
    query.promote_name = name
    if component:
        query.component = component
    promotions = dlrn_client.api_promotions_get(query)
    if promotions:
        last_promotion = promotions[0].to_dict()
        last_promotion['release'] = release
        last_promotion['distro'] = distro
        # sanitize dict
        if last_promotion['component'] is None:
            last_promotion['component'] = "none"
        return last_promotion
    return


def get_promotion(url, release, distro, component):
    promoter_config = promoter_utils.get_promoter_config(
        url, release, distro, component
    )

    dlrn_client = promoter_utils.get_dlrn_client(promoter_config)

    promotions = []
    for promotion_name in promoter_config['promote_from']:
        if component is None:
            promo = get_last_promotion(
                dlrn_client, release, distro, promotion_name
            )
            consistent = format_ts_from_last_modified(
                promoter_utils.get_consistent(promoter_config))
            if promo:
                promotion_details = promoter_utils.get_url_promotion_details(
                    promoter_config, promo)
        else:
            promo = get_last_promotion(
                dlrn_client, release, distro, promotion_name, component
            )
            consistent = format_ts_from_last_modified(
                promoter_utils.get_consistent(promoter_config, component)
            )
            promotion_details = "None"
        # get the promotion for consistent to establish how old the
        # promotion is.  date(promomtion) - date(consistent)
        if promo and consistent:
            promo.update({'consistent_date': consistent})
        if promo and promotion_details:
            promo.update({'promotion_details': promotion_details})
        if promo:
            promotions.append(influxdb(promo))

    return promotions


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Print release last promotions as influxdb lines",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '--release',
        required=True,
        choices=[
            'rhos-17', 'rhos-16.2', 'master', 'ussuri', 'train', 'stein',
            'rocky', 'queens'
        ],
        help='Upstream or downstream release.'
    )
    parser.add_argument(
        '--distro',
        default='CentOS-7',
        choices=['CentOS-7', 'CentOS-8', 'RedHat-8'],
        help='Distribution to query.'
    )
    parser.add_argument(
        '--component',
        default=None,
        help='Specific OpenStack component (e.g., compute, security).'
    )
    parser.add_argument(
        '--url',
        default=DEFAULT_PROMOTER_BASE_URL,
        help='Promoter repository base URL.'
    )
    args = parser.parse_args()
    promotions = get_promotion(args.url, args.release, args.distro, args.component)
    for promotion in promotions:
        print(promotion)
