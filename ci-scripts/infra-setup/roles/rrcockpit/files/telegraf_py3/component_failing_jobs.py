import click
import requests
import yaml
import find_jobs_in_criteria
import dlrnapi_client
from dlrnapi_client.rest import ApiException

def fetch_hashes_from_commit_yaml(url):
    """
    This function finds commit hash , distro hash, extended_hash from commit.yaml
    :param url for commit.yaml
    :returns strings for commit_hash, distro_hash, extended_hash
    """
    commit_yaml_content = find_jobs_in_criteria.url_response_in_yaml(url)
    commit_hash = commit_yaml_content['commits'][0]['commit_hash']
    distro_hash = commit_yaml_content['commits'][0]['distro_hash']
    extended_hash = commit_yaml_content['commits'][0]['extended_hash']

    return commit_hash, distro_hash, extended_hash


# Find the list of passing jobs from dlrn.
    ## Inputs will be api_url, commit hash , distro hash, extended_hash
def find_results_from_dlrn_repo_status(api_url, commit_hash, distro_hash, extended_hash):
    """ This function returns api_response from dlrn for a particular commit_hash, distro_hash, extended_hash
    https://github.com/softwarefactory-project/dlrnapi_client/blob/master/docs/DefaultApi.md#api_repo_status_get
    :param api_url: the dlrn api endpoint for a particular release
    :param commit_hash: For a particular repo, commit.yaml contains this info.
    :param distro_hash: For a particular repo, commit.yaml contains this info.
    :param extended_hash: For a particular repo, commit.yaml contains this info.
    :return api_response: from dlrnapi server containing result of passing/failing jobs
    """
    if extended_hash == "None":
        extended_hash = None
    api_client = dlrnapi_client.ApiClient(host=api_url)
    api_instance = dlrnapi_client.DefaultApi(api_client)
    params = dlrnapi_client.Params2(commit_hash=commit_hash, distro_hash=distro_hash, extended_hash=extended_hash)
    try:
        api_response = api_instance.api_repo_status_get(params=params)
    except ApiException as e:
        print("Exception when calling DefaultApi->api_repo_status_get: %s\n" % e)
    return api_response


## Main script should take:

    ## component arg

@ click.command()
@ click.option("--release", default='master',
               type=click.Choice(['master', 'wallaby', 'victoria', 'ussuri',
                                  'train', 'osp17', 'osp16-2']))
@ click.option("--component",
               type=click.Choice(["baremetal", "cinder", "clients", "cloudops", "common", "compute",
                  "glance", "manila", "network", "octavia", "security", "swift",
                  "tempest", "tripleo", "ui", "validation"]))

def main(release, component):
    """ Find the failing jobs which are blocking promotion of a component.
    :param release: The OpenStack release e.g. wallaby
    :param component:
    """

    if component:
        all_components = [component]
    else:
        all_components = ["baremetal", "cinder", "clients", "cloudops", "common", "compute",
                          "glance", "manila", "network", "octavia", "security", "swift",
                          "tempest", "tripleo", "ui", "validation"]

    ## find api_url from criteria file
    ## Input: Url of criteria file
    ## Output: api_url - string
    url = 'http://10.0.148.74/config/CentOS-8/component/' + release + '.yaml'
    api_url, base_url = find_jobs_in_criteria.gather_basic_info_from_criteria(url)
    for component in all_components:
        print(f"Testing {component}")
        commit_url = base_url + 'component/' + component + '/component-ci-testing/commit.yaml'
        commit_hash, distro_hash, extended_hash = fetch_hashes_from_commit_yaml(commit_url)
        print(f"{api_url}/api/civotes_detail.html?commit_hash={commit_hash}&distro_hash={distro_hash}&extended_hash={extended_hash}")
        api_response = find_results_from_dlrn_repo_status(api_url, commit_hash, distro_hash, extended_hash)
        all_jobs, passed_jobs, failed_jobs = find_jobs_in_criteria.conclude_results_from_dlrn(api_response)
        # Find the list of jobs which are in component promotion criteria
        ## Input:  Url of criteria file.
        ## list containing jobs which are in promotion criteria.
        jobs_in_criteria = set(find_jobs_in_criteria.find_jobs_in_component_criteria(url, component))

        ## Find:-
         ## All passing jobs
        ## Jobs whose run is missing in promotion criteria.
        ## Jobs which failed/run missing and present in promotions criteria
        ## Jobs which failed but not in promotion criteria
        jobs_which_need_pass_to_promote = jobs_in_criteria.difference(passed_jobs)
        jobs_with_no_result = jobs_in_criteria.difference(all_jobs)
        print("Jobs which are in promotion criteria and need pass to promote the Hash: ")
        if jobs_which_need_pass_to_promote:
            print(jobs_which_need_pass_to_promote)
        else:
            print("all jobs in criteria passed")
        print("\n")



if __name__ == '__main__':
    main()
