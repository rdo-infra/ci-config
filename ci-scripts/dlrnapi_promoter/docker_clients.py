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
                "serveraddress": self.host
            }
            self.auth_pair = (self.username, self.password)
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
            self.auth_url = None

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
        session.headers['Accept'] = \
            "application/vnd.docker.distribution.manifest.v2+json"
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

    def manifest_delete(self, repo, digest):
        session = requests.Session()
        url = "{}/{}/manifests/{}".format(self.api_url, repo, digest)
        session.headers.update(self.raw_api_headers)
        self.log.debug("Calling api request DELETE %s", url)
        res = session.delete(url, verify=False, auth=self.auth_pair)
        self.log.debug("Api response: %s %s", res.headers, res.status_code)
        if res.status_code >= 300:
            self.log.error("Api response: %s %s %s", res.headers,
                           res.status_code,
                           res.text)

    def tag(self, source_name, dest_name):
        manifest = self.manifest_get(source_name.base_namespace,
                                     source_name.tag)
        self.manifest_put(manifest, dest_name.base_namespace,
                          dest_name.tag)

    def image_delete(self, name, tag):
        manifest = self.manifest_get(name, tag)
        self.manifest_delete(name, manifest['layers']['digest'])

    def exists(self, image_name):
        return self.manifest_exists(image_name.base_namespace, image_name.tag)

    def manifest_list_put(self, list_name, images):

        image_manifests_list = []
        for image in images:
            manifest_list_element = {
                "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                "size": image.get_size(),
                "digest": image.get_digest(),
                "platform": {
                    "architecture": image.platform,
                    "os": image.os,
                }
            }
            image_manifests_list.append(manifest_list_element)

        manifest_list = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.list"
                         ".v2+json",
            "manifests": image_manifests_list,
        }
        self.manifest_put(manifest_list, list_name.full_no_tag, list_name.tag)


class DockerImagesClient(object):

    log = logging.getLogger("promoter")

    def __init__(self):
        self.docker_client = docker.from_env()

    def remove(self, image_name, force=False):
        try:
            self.docker_client.images.remove(image_name.full, force=force)
        except docker.errors.ImageNotFound:
            pass

    def pull(self, image_name):
        try:
            local_image = self.docker_client.images.pull(image_name.full_no_tag,
                                                         tag=image_name.tag)
        except docker.errors.ImageNotFound:
            self.log.error("No image associated with this repo")
            raise
        return local_image

    def get(self, image_name):
        local_image = None
        try:
            local_image = self.docker_client.images.get(image_name.full)
        except docker.errors.ImageNotFound:
            pass

        return local_image

    def tag(self, old_name, new_name):
        image = self.get(old_name)
        image.tag(new_name.full_no_tag, new_name.tag)

    def push(self, image_name):
        try:
            status_messages = self.docker_client.images.push(
                image_name.full_no_tag,
                tag=image_name.tag,
                stream=True,
                decode=True)
        except docker.errors.APIError:
            self.log.error("Error pushing")
            raise

        for status in status_messages:
            if 'error' in status:
                self.log.error("Error while pushing %s: %s", image_name.full,
                               status['error'])

                raise Exception("Push failed")

    def get_digest(self, image_name):
        local_image = self.get(image_name)
        digest = None
        try:
            digest = local_image.attrs["ContainerConfig"]["Image"]
        except (KeyError, AttributeError):
            pass

        return digest

    def get_size(self, image_name):
        local_image = self.get(image_name)
        size = 0
        try:
            size = local_image.attrs["Config"]["Size"]
        except (KeyError, AttributeError):
            pass

        return size


