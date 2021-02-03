import dlrnapi_client
import requests
import yaml


def get_promoter_config(base_url, release, distro, component):
    integration_tail = "/ci-scripts/dlrnapi_promoter/config_environments" \
                       "/rdo/{}/{}.yaml"
    component_tail = "/ci-scripts/dlrnapi_promoter/config/{}/component/{}.yaml"

    if component:
        tail = component_tail
    else:
        tail = integration_tail

    url_template = base_url.rstrip('/') + tail
    url = url_template.format(distro, release)
    response = requests.get(url)

    if response.ok:
        config = yaml.load(response.text, Loader=yaml.FullLoader)
    else:
        raise Exception(
            'Unable to fetch promoter configuration from {}'.format(url)
        )

    return config


def get_dlrn_client(config, component):
    # TO-DO normalize component and intergration config
    if component is None:
        api_client = dlrnapi_client.ApiClient(host=config['api_url'])
    else:
        api_client = dlrnapi_client.ApiClient(host=config['api_url'])
    return dlrnapi_client.DefaultApi(api_client=api_client)


# get the date of the consistent link in dlrn
def get_consistent(config, component=None):
    if component is None:
        response = requests.get(
            config['base_url'] + 'consistent/delorean.repo')
        if response.ok:
            consistent_date = response.headers['Last-Modified']
        else:
            return None
    else:
        # TO-DO normalize component and intergration config
        response = requests.get(
            config['base_url'] + 'component/'
            + component + '/consistent/delorean.repo')
        if response.ok:
            consistent_date = response.headers['Last-Modified']
        else:
            return None

    return consistent_date


def get_url_promotion_details(config, promotion_data, component):
    promotion = str(promotion_data['promote_name'])
    # TO-DO, this doesn't make sense yet
    if component:
        response = requests.get(
            config['base_url'] + promotion + '/delorean.repo.md5')
    else:
        response = requests.get(
            config['base_url'] + promotion + '/delorean.repo.md5')

    if response.ok and not component:
        aggregate_hash = response.content.decode()
        url = (config['api_url']
               + '/api/civotes_agg_detail.html?ref_hash='
               + aggregate_hash)
    else:
        commit_hash = promotion_data['commit_hash']
        distro_hash = promotion_data['distro_hash']
        if component:
            url = (config['api_url']
                   + '/api/civotes_detail.html?commit_hash='
                   + commit_hash + '&'
                   + 'distro_hash=' + distro_hash)
        else:
            url = (config['api_url']
                   + '/api/civotes_detail.html?commit_hash='
                   + commit_hash + '&'
                   + 'distro_hash=' + distro_hash)

    return url
