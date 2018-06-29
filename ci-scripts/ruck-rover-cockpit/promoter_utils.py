
import dlrnapi_client
import ConfigParser
import requests

from StringIO import StringIO

PROMOTER_CONFIG_URL=("https://raw.githubusercontent.com/rdo-infra/ci-config/"
                     "master/ci-scripts/dlrnapi_promoter/config/{}.ini")

def get_promoter_config(release):

    response = requests.get(
            PROMOTER_CONFIG_URL.format(release))

    if response.ok:
        config = ConfigParser.SafeConfigParser(allow_no_value=True)
        config.readfp(StringIO(response.content))
        return config
    else:
        return None


def get_dlrn_instance(config = None):

    if config is None:
        return None

    api_client = dlrnapi_client.ApiClient(host=config.get('main', 'api_url'))
    return dlrnapi_client.DefaultApi(api_client=api_client)

def get_dlrn_instance_for_release(release):
    promoter_config = get_promoter_config(release)
    if promoter_config:
        return get_dlrn_instance(promoter_config)

