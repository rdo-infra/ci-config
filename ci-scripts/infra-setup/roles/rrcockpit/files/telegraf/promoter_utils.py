import dlrnapi_client
import ConfigParser
import requests
import yaml

from StringIO import StringIO

PROMOTER_CONFIG_URL = ("https://raw.githubusercontent.com/rdo-infra/ci-config/"
                       "master/ci-scripts/dlrnapi_promoter/config/{}/{}.ini")

COMPONENT_CONFIG_URL = (https: // raw.githubusercontent.com / rdo - infra / ci - config /"
                        "master/ci-scripts/dlrnapi_promoter/"
                        "config/{}/component/{}.yaml)"


def get_promoter_config(release, distro='CentOS-7'):

    response=requests.get(PROMOTER_CONFIG_URL.format(distro, release))

    if response.ok:
        # https://docs.python.org/3/library/configparser.html
        config=ConfigParser.SafeConfigParser(allow_no_value=True)
        config.readfp(StringIO(response.content))
        return config
    else:
        return None

def get_promoter_component_config(release, distro='CentOS-8'):

    response=requests.get(COMPONENT_CONFIG_URL.format(distro, release)).text

    if response.ok:
        config=yaml.load(response, Loader=yaml.FullLoader)
        return config
    else:
        return None


def get_dlrn_instance(config=None):

    if config is None:
        return None

    if isinstance(config, dict):
        api_client=dlrnapi_client.ApiClient(host=config['main']['api_url'])
    else:
        api_client=dlrnapi_client.ApiClient(host=config.get('main', 'api_url'))

    return dlrnapi_client.DefaultApi(api_client=api_client)


def get_dlrn_instance_for_release(release):
    promoter_config=get_promoter_config(release)
    if promoter_config:
        return get_dlrn_instance(promoter_config)
