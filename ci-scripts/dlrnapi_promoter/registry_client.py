import base64
import copy
import json
import logging
import requests

from containers_lists import ImageList


class DockerRegistryApiClient(object):

    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.namespace = config['namespace']
        self.containers_list = None
        self.name = config['name']
        self.host = config['host']
        self.port = config['port']
        self.secure = config['secure']
        self.registry = "{}:{}".format(self.host, self.port)
        if self.secure:
            self.username = config['username']
            self.password = config['password']
            self.protocol = "https://"
            auth_data = {
                "username": self.username,
                "password": self.password,
                "email": "",
                "serveraddress": "self.host"
            }
            self.auth_pair = (self.username, self.password)
            self.client.login(self.username, self.password,
                              registry=self.host,
                              reauth=True)
            # X-Rgistry-Auth header to be passed to all post operations
            auth_json = json.dumps(auth_data).encode('ascii')
            x_registry_auth = base64.urlsafe_b64encode(auth_json)
            self.raw_api_headers = {
                "X-Registry-Auth": x_registry_auth,
                "Content-Type": "application/json",
            }
            # for docker.io we need special treatment for each request,
            # we get the
            # token, then we pass it with every request.
            auth_url = "https://auth.docker.io/token?service=registry.docker" \
                       ".io&scope" \
                       "=repository:{}:push,pull"
        else:
            self.auth_pair = ()
            self.raw_api_headers = {}
            self.protocol = "http://"

        self.api_url = "{}{}:{}/v2/".format(self.protocol, self.host, self.port)

    def manifest_exists(self, repo, tag):
        session = requests.Session()
        url = "{}/{}/manifests/{}".format(self.api_url, repo, tag)
        session.headers.update(self.raw_api_headers)
        res = session.head(url, verify=False, auth=self.auth_pair)
        if not res.ok:
            return False
        return True

    def manifest_get(self, repo, tag):
        session = requests.Session()
        session.headers.update(self.raw_api_headers)
        session.headers[
            'Accept'] = "application/vnd.docker.distribution.manifest.v2+json"
        url = "{}/{}/manifests/{}".format(self.api_url, repo, tag)
        res = session.get(url, verify=False,
                          auth=(self.username, self.password))

        if not res.ok:
            return {}

        return json.loads(res.text)

    def manifest_post(self, manifest, repo, tag):
        session = requests.Session()
        session.headers.update(self.raw_api_headers)
        url = "{}/{}/manifests/{}".format(self.api_url, repo, tag)
        res = session.post(url, data=manifest, verify=False,
                           auth=(self.username, self.password))

        if not res.ok:
            raise Exception("OMG")


class RegistryClient(object):

    def __init__(self, config):
        self.config = config
        self.api_client = DockerRegistryApiClient(config)
        self.images_lists = {}
        self.namespace = config['namespace']
        self.registry = "{}:{}".format(self.host, self.port)

    def add_list(self, list_name, tag, **kwargs):
        image_list = ImageList(self.registry, self.namespace, tag, **kwargs)
        self.images_lists[list_name] = image_list

    def load_list(self, src_registry, list_name):
        pass

    def repo_push(self, src_repos, filters={}, src_registry=None):
        """ Push images from a repo list
        """
        if isinstance(src_repos, str):
            src_repos = [src_repos]

        src_repos = self.containers_filter(src_repos, filters)

        retagged_repos = self.local_retag(src_repos, src_registry=src_registry)
        for repo_name, repo_tag in retagged_repos:
            self.client.images.push(repo_name, tag=repo_tag)

    def tag_compare(self, repo, tag, other_tag):
        if not (self.manifest_exists(repo, tag)
                and self.manifest_exists(repo, other_tag)):
            return False

        manifest = self.manifest_get(repo, tag)
        other_manifest = self.manifest_get(repo, other_tag)
        digest = manifest['config']['digest']
        other_digest = other_manifest['config']['digest']

        return digest == other_digest

    def cleanup(self):
        for batch in self.batches:
            self.local_remove(batch_name=batch)

    def validate_containers(self, dlrn_hash, list_name, name=None,
                            assume_valid=False):
        # Check we have all the containers we need to roll back to
        # if name is specified, verify that name points to the hash

        # containers_valid: a repo/dlrn_hash must exists for all the
        # containers
        # containers_missing and containers_present: are complementary
        # They give easy access to what's missing
        # if a name is given:
        # comparisons: will contain a dictionary of repo, boolean value
        # representing if name and dlrn_hash point to the same repo
        # promotion_valid: true if all the containers are compared successfully
        results = {
            "hash_valid": False,
            "containers_missing": copy.copy(containers_list),
            "containers_present": [],
            "comparisons": {},
            "promotion_valid": name is not None,
        }
        if assume_valid:
            results = {
                "hash_valid": True,
                "containers_present": copy.copy(containers_list),
                "containers_missing": [],
                "comparisons": {},
                "promotion_valid": True,
            }
            return results

        count = 0
        repos = self.lists[list_name]
        for repo in repos:
            if repo.remote_exists():
                count += 1
                results['containers_present'].append(repo)
                results['containers_missing'].remove(repo)
            if name is not None:
                res = self.tag_compare(repo, dlrn_hash.full_hash, name)
                if not res:
                    results['promotion_valid'] = False
                results['comparison'][container_name] = res

        if count == len(repos):
            results['hash_valid'] = True

        return results






