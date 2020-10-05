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

PROMOTER_CONFIG_URL = ("https://raw.githubusercontent.com/rdo-infra/ci-config/"
                       "master/ci-scripts/dlrnapi_promoter/config/{}/{}.ini")

COMPONENT_CONFIG_URL = ("https://raw.githubusercontent.com/rdo-infra/ci-config/"
                        "master/ci-scripts/dlrnapi_promoter/"
                        "config/{}/component/{}.yaml")


def get_promoter_config(release, distro='CentOS-7'):

    response = requests.get(PROMOTER_CONFIG_URL.format(distro, release))

    if response.ok:
        config = ConfigParser.SafeConfigParser(allow_no_value=True)
        config.readfp(StringIO(response.content))
        config = config._sections
        return config
    else:
        return None


def get_promoter_component_config(release, distro='CentOS-8'):

    response = requests.get(COMPONENT_CONFIG_URL.format(distro, release))

    if response.ok:
        config = yaml.load(response.text, Loader=yaml.FullLoader)
        return config
    else:
        return None


def get_dlrn_instance(config=None):

    if config is None:
        return None

    if isinstance(config, dict):
        api_client = dlrnapi_client.ApiClient(host=config['main']['api_url'])
    else:
        api_client = dlrnapi_client.ApiClient(
            host=config.get('main', 'api_url'))

    return dlrnapi_client.DefaultApi(api_client=api_client)


def get_dlrn_instance_for_release(release):
    promoter_config = get_promoter_config(release)
    if promoter_config:
        return get_dlrn_instance(promoter_config)

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
