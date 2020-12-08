import dlrnapi_client
import requests
import six
import yaml

if six.PY2:
    import ConfigParser
    from StringIO import StringIO
elif six.PY3:
    import configparser as ConfigParser
    from io import StringIO


def get_promoter_config(base_url, release, distro, component):

    integration_tail = "/ci-scripts/dlrnapi_promoter/config/{}/{}.ini"
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


def get_dlrn_client(config):
    api_client = dlrnapi_client.ApiClient(host=config['main']['api_url'])
    return dlrnapi_client.DefaultApi(api_client=api_client)


# get the date of the consistent link in dlrn
def get_consistent(config, component=None):
    if component is None:
        response = requests.get(
            config['main']['base_url'] + 'consistent/delorean.repo')
        if response.ok:
            consistent_date = response.headers['Last-Modified']
        else:
            return None
    else:
        response = requests.get(
            config['main']['base_url'] + 'component/'
            + component + '/consistent/delorean.repo')
        if response.ok:
            consistent_date = response.headers['Last-Modified']
        else:
            return None

    return consistent_date


def get_url_promotion_details(config, promotion_data):
    promotion = str(promotion_data['promote_name'])
    response = requests.get(
        config['main']['base_url'] + promotion + '/delorean.repo.md5')
    if response.ok:
        aggregate_hash = response.content
        url = (config['main']['api_url']
               + '/api/civotes_agg_detail.html?ref_hash='
               + aggregate_hash)
    else:
        commit_hash = promotion_data['commit_hash']
        distro_hash = promotion_data['distro_hash']
        url = (config['main']['api_url']
               + '/api/civotes_detail.html?commit_hash='
               + commit_hash + '&'
               + 'distro_hash=' + distro_hash)

    return url
