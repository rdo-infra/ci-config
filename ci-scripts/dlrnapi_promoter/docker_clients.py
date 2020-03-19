import base64
import json
import logging

import docker
import requests


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

        self.api_url = "{}{}:{}/v2".format(self.protocol, self.host, self.port)

    def manifest_exists(self, repo, tag):
        session = requests.Session()
        url = "{}/{}/manifests/{}".format(self.api_url, repo, tag)
        session.headers.update(self.raw_api_headers)
        self.log.debug("Calling api request HEAD %s", url)
        res = session.head(url, verify=False, auth=self.auth_pair)
        self.log.debug("Api response: %s %s", res.headers, res.status_code)
        if res.status_code < 300:
            return True
        return False

    def manifest_get(self, repo, tag):
        session = requests.Session()
        session.headers.update(self.raw_api_headers)
        session.headers[
            'Accept'] = "application/vnd.docker.distribution.manifest.v2+json"
        url = "{}/{}/manifests/{}".format(self.api_url, repo, tag)
        self.log.debug("Calling api request GET %s", url)
        res = session.get(url, verify=False, auth=self.auth_pair)
        self.log.debug("Api response: %s %s", res.headers, res.status_code)
        if res.status_code < 300:
            return json.loads(res.text)
        else:
            self.log.error("Api response: %s %s %s", res.headers,
                           res.status_code,
                           res.text)
            raise Exception

    def manifest_put(self, manifest, repo, tag):
        session = requests.Session()
        session.headers.update(self.raw_api_headers)
        session.headers['Content-type'] = \
            "application/vnd.docker.distribution.manifest.v2+json"
        url = "{}/{}/manifests/{}".format(self.api_url, repo, tag)
        self.log.debug("Calling api request PUT %s", url)
        res = session.put(url, json=manifest, verify=False,
                          auth=self.auth_pair)
        self.log.debug("Api response: %s %s %s", res.headers, res.status_code,
                       res.text)

        if not res.ok:
            self.log.error("Api response: %s %s %s", res.headers,
                           res.status_code,
                           res.text)
            raise Exception


class DockerClient(object):

    def __new__(cls):
        return docker.from_env().images
