#!/usr/bin/env python

import argparse

import dlrnapi_client
from influxdb_utils import format_ts_from_float, format_ts_from_last_modified

# only run upstream or downstream promotion checks
# do not run both.
# try:
#    from internal_promoter_utils import (get_consistent, get_dlrn_instance,
#                                         get_promoter_component_config,
#                                         get_promoter_config)
# except ImportError:
from promoter_utils import (get_consistent, get_dlrn_instance,
                            get_promoter_component_config,
                            get_promoter_config,
                            get_url_promotion_details)

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
        # sanitize dict
        if last_promotion['component'] is None:
            last_promotion['component'] = "none"
        return last_promotion
    return


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Print release last promotions as influxdb lines")

    parser.add_argument('--release', required=True)
    parser.add_argument('--distro', default="CentOS-7")
    parser.add_argument('--component', default=None)
    args = parser.parse_args()

    if args is None:
        SystemExit(1)

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
                consistent = format_ts_from_last_modified(
                    get_consistent(promoter_config))
                if promo:
                    promotion_details = get_url_promotion_details(
                        promoter_config, promo)
            else:
                promo = get_last_promotion(dlrn, args.release, args.distro,
                                           promotion_name, args.component)
                consistent = format_ts_from_last_modified(
                    get_consistent(promoter_config, args.component))
                promotion_details = "None"
            # get the promotion for consistent to establish how old the
            # promotion is.  date(promomtion) - date(consistent)
            if promo and consistent:
                promo.update({'consistent_date': consistent})
            if promo and promotion_details:
                promo.update({'promotion_details': promotion_details})
            if promo:
                print(influxdb(promo))
    else:
        print('the dlrn configuration was not found')
