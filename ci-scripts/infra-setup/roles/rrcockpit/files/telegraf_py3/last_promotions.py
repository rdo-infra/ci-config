#!/usr/bin/env python

import argparse

import dlrnapi_client
import promoter_utils
from influxdb_utils import format_ts_from_float, format_ts_from_last_modified

PROMOTION_INFLUXDB_LINE = ("dlrn-promotion,"
                           "release={release},distro={distro},"
                           "name={promote_name} "
                           "commit_hash=\"{commit_hash}\","
                           "distro_hash=\"{distro_hash}\","
                           "repo_hash=\"{repo_hash}\","
                           "repo_url=\"{repo_url}\","
                           "consistent_date={consistent_date},"
                           "promotion_details=\"{promotion_details}\","
                           "component=\"{component}\","
                           "extended_hash=\"{extended_hash}\" "
                           "{timestamp}")

DEFAULT_PROMOTER_BASE_URL = (
    "https://raw.githubusercontent.com/rdo-infra/ci-config/master"
)


def influxdb(promotion):
    if 'extended_hash' not in promotion.keys():
        promotion['extended_hash'] = None
    promotion['timestamp'] = format_ts_from_float(promotion['timestamp'])
    return PROMOTION_INFLUXDB_LINE.format(**promotion)


def get_dlrn_client(url, release, distro, component):
    promoter_config = promoter_utils.get_promoter_config(
        url, release, distro, component
    )
    dlrn_client = promoter_utils.get_dlrn_client(promoter_config, component)
    return dlrn_client


def get_dlrn_promotions(dlrn_client, name, component=None):
    query = dlrnapi_client.PromotionQuery()
    query.promote_name = name
    if component:
        query.component = component
    promotions = dlrn_client.api_promotions_get(query)
    return promotions


def get_last_promotion(promotions, release, distro, component=None):
    if promotions:
        # TO-DO
        # perhaps loop through the promotions and
        # ensure [0] is in fact the latest
        last_promotion = promotions[0].to_dict()
        last_promotion['release'] = release
        last_promotion['distro'] = distro
        # sanitize dict
        if last_promotion['component'] is None:
            last_promotion['component'] = "none"
        return last_promotion
    return


def update_promotion(promo, promotion_details, consistent):

    if promo and consistent:
        promo.update({'consistent_date': consistent})
    if promo and promotion_details:
        promo.update({'promotion_details': promotion_details})

    return promo


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Print release last promotions as influxdb lines",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '--release',
        required=True,
        choices=[
            'rhos-17', 'rhos-16.2', 'master', 'wallaby', 'victoria', 'ussuri', 'train',
            'stein', 'rocky', 'queens'
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
    promotions = []
    args = parser.parse_args()

    promoter_config = promoter_utils.get_promoter_config(args.url,
                                                         args.release,
                                                         args.distro,
                                                         args.component)

    dlrn_client = get_dlrn_client(args.url,
                                  args.release,
                                  args.distro,
                                  args.component)
    # with components we are only concerned with promotions to
    # promoted-components
    if args.component is not None:
        promoter_config['promotions'] = ["promoted-components"]

    for promotion_name in promoter_config['promotions']:
        promos = get_dlrn_promotions(dlrn_client,
                                     promotion_name,
                                     args.component)

        promo = get_last_promotion(promos,
                                   args.release,
                                   args.distro,
                                   args.component)

        if promo:
            promotion_details = promoter_utils.get_url_promotion_details(
                promoter_config, promo, args.component)

            consistent = format_ts_from_last_modified(
                promoter_utils.get_consistent(promoter_config, args.component))

            promo = update_promotion(promo,
                                     promotion_details,
                                     consistent)
            promotions.append(promo)

    for promotion in promotions:
        print(influxdb(promotion))
