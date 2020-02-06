import docker
import logging

domain_key = '''
-----BEGIN PRIVATE KEY-----
MIIBVQIBADANBgkqhkiG9w0BAQEFAASCAT8wggE7AgEAAkEA45UGl1ZcyDOqY3ZP
/JlTyzSbPjgNc6feIi3VdgA1kXoVlvvDU40+E6RrRj2TjSVMo3Dtci+d72HIe+3/
ZW5vzQIDAQABAkEAhn4peQI2rrGpvkHLH1JVbL9YBzsE6BaKddR0U9nnzmIkS4cN
w3qheYMXwwJW+qvpF9y0AwCNe/tr+8A/39zmWQIhAPY1wmw1DNh4FeGLevld9AQI
gL9tyodatfQt/6aon6MnAiEA7KGl5GUUPXH2ujtmkQ5ZTSC8hJT2Slvfju7JgXd9
3esCIG1Tr9J2uA6DPEwbsG58jrcfw3O9X9o8qGEV79hkNgavAiAfAh/HCifY1XJL
fTU3lPXG0Z9ikFKl89wb0ta9DHeF+QIhAOVIvYiRt5NIjVQApscF5I29VLAiCTbK
w+U3R5J223s/
-----END PRIVATE KEY-----
'''

domain_crt = '''
-----BEGIN CERTIFICATE-----
MIIB1jCCAYCgAwIBAgIJAIhu0kwOc4vYMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMTkxMTE1MTExODI3WhcNMjAxMTE0MTExODI3WjBF
MQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50
ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAOOV
BpdWXMgzqmN2T/yZU8s0mz44DXOn3iIt1XYANZF6FZb7w1ONPhOka0Y9k40lTKNw
7XIvne9hyHvt/2Vub80CAwEAAaNTMFEwHQYDVR0OBBYEFGDiDqwoC133Ajf0SvbB
/guLaJapMB8GA1UdIwQYMBaAFGDiDqwoC133Ajf0SvbB/guLaJapMA8GA1UdEwEB
/wQFMAMBAf8wDQYJKoZIhvcNAQELBQADQQBtZx3kFw6cWBM7OBccvO0tg1G2DdjQ
ROqmK1Dhcd2F0NUvAevJMhWDj5Cy6rehMBRlhgfCYZs9tMAlG6mCm6q9
-----END CERTIFICATE-----
'''

# "username":"password"
htpasswd = ("username:"
            "$2y$05$awdjjCuIy8riH6xLa37EJeC4hFbjZ4KRIVaoMMqEFaktoAfy8B2XW")

class BaseImage(object):

    log = logging.getLogger("promoter-staging")

    def __init__(self, build_tag):
        self.client = docker.from_env()
        self.build_tag = build_tag

    def build(self):
        try:
            self.image = self.client.images.get(self.build_tag)
        except docker.errors.ImageNotFound:
            temp_dir = tempfile.mkdtemp()
            with open(os.path.join(temp_dir, "nothing"), "w"):
                pass
            with open(os.path.join(temp_dir, "Dockerfile"), "w") as df:
                df.write("FROM scratch\nCOPY nothing /\n")
            self.image, _ = self.client.images.build(path=temp_dir,
                                                     tag=self.build_tag)
            shutil.rmtree(temp_dir)

        return self.image

    def remove(self):
        self.client.images.remove(self.image.id, force=True)


class LocalRegistry(object):
    """
    This class handles creation of registries using basic registry image
    eventually applying configuration when a password protected registry
    is needed.
    """

    log = logging.getLogger("promoter-staging")

    def __init__(self, name, port=None, secure=False, schema="v2_s2"):
        self.port = port
        self.name = name
        self.docker_client = docker.from_env()
        self.docker_containers = self.docker_client.containers
        self.docker_images = self.docker_client.images
        self.container = None
        self.secure = secure
        self.schema = schema
        if self.schema != "v2_s2":
            raise Exception("Only registries with API v2_s2 are supported")
        else:
            self.base_image = "registry:2"
        self.base_secure_image = "registry:2secure"
        if self.secure:
            self.registry_image = self.get_secure_image()
        else:
            self.registry_image = self.get_base_image()

    def get_base_image(self):
        """
        Get the base registry image, trying locally first
        """
        try:
            registry_image = self.docker_images.get(
                self.base_image)
        except docker.errors.ImageNotFound:
            self.log.info("Downloading registry image")
            registry_image = self.docker_images.pull(
                "docker.io/{}".format(self.base_image))

        return registry_image

    def get_secure_image(self):
        """
        Try to get image locally, then eventually build it
        """
        try:
            registry_image = self.docker_images.get(
                self.base_secure_image)
        except docker.errors.ImageNotFound:
            self.get_base_image()
            registry_image = self.build_secure_image()

        return registry_image

    def build_secure_image(self):
        """
        The method build a new image using the default registry:2 image as a
        starting point, restricting access with credentials and injecting a
        self-signed certificate
        """
        temp_dir = tempfile.mkdtemp()
        os.mkdir(os.path.join(temp_dir, "auth"))
        os.mkdir(os.path.join(temp_dir, "certs"))
        domain_key_path = os.path.join(temp_dir, "certs", "domain.key")
        with open(domain_key_path, "w") as key_file:
            key_file.write(domain_key)
        domain_crt_path = os.path.join(temp_dir, "certs", "domain.crt")
        with open(domain_crt_path, "w") as crt_file:
            crt_file.write(domain_crt)
        htpasswd_path = os.path.join(temp_dir, "auth", "htpasswd")
        with open(htpasswd_path, "w") as pass_file:
            pass_file.write(htpasswd)
        with open(os.path.join(temp_dir, "Dockerfile"), "w") as df:
            df.write("FROM {}\n"
                     "COPY auth/ /auth/\n"
                     "COPY certs/ /certs/\n"
                     "".format(self.base_image))
        image, _ = self.docker_client.images.build(path=temp_dir,
                                                   tag=self.base_secure_image)
        shutil.rmtree(temp_dir)

        return image

    def is_running(self):
        try:
            self.container = self.docker_containers.get(self.name)
            return True
        except docker.errors.NotFound:
            self.container = None
            return False

    def run(self):
        if self.is_running():
            self.log.info("Registry %s already running", self.name)
            return

        kwargs = {
            'name': self.name,
            'detach': True,
            'restart_policy': {
                'Name': 'always',
            },
            'ports': {
                '5000/tcp': self.port
            },
        }
        if self.secure:
            kwargs["environment"] = {
                "REGISTRY_AUTH": "htpasswd",
                "REGISTRY_AUTH_HTPASSWD_REALM": "Registry Realm",
                "REGISTRY_AUTH_HTPASSWD_PATH": "/auth/htpasswd",
                "REGISTRY_HTTP_TLS_CERTIFICATE": "/certs/domain.crt",
                "REGISTRY_HTTP_TLS_KEY": "/certs/domain.key",
            }
        self.container = self.docker_containers.run(self.registry_image.id,
                                                    **kwargs)
        self.log.info("Created registry %s", self.name)

    def stop(self):
        if not self.is_running():
            self.log.info("Registry %s not running, not stopped", self.name)
            return

        self.container.stop()
        self.container.remove()
        self.container = None


class StagingRegistries(object):

    def __init__(self):
        self.docker_client = docker.from_env()

    def setup_registries(self):
        results = {}
        for registry_conf in self.config['registries']:
            if registry_conf['type'] == "source" and "source" in results:
                continue
            if registry_conf['type'] == "source":
                results.update({
                    'source': {
                        'host': "localhost:{}".format(registry_conf['port']),
                        'name': registry_conf['name'],
                        'namespace': self.config['containers']['namespace'],
                        'username': 'unused',
                        'password': 'unused',
                        'schema': registry_conf['schema']
                    }
                })
            else:
                if "targets" not in results:
                    results['targets'] = []
                result_registry = {
                    'host': "localhost:{}".format(registry_conf['port']),
                    'name': registry_conf['name'],
                    'namespace': self.config['containers']['namespace'],
                    'username': 'unused',
                    'password': 'unused',
                    'schema': registry_conf['schema'],
                }
                if registry_conf['secure']:
                    result_registry['username'] = 'username'
                    result_registry['password'] = 'password'
                    auth_url = ("https://localhost:{}"
                                "".format(registry_conf['port']))
                    result_registry['auth_url'] = auth_url
                results['targets'].append(result_registry)
            if self.config['dry-run']:
                continue

            # TODO(gcerami) Just pass registry_conf at this point.
            registry = Registry(registry_conf['name'],
                                port=registry_conf['port'],
                                secure=registry_conf['secure'],
                                schema=registry_conf['schema'])
            registry.run()

        self.config['results']['registries'] = results


    def generate_pattern_file(self):
        """
        The container-push playbook of the real promoter gets a list of
        containers from a static position in a tripleo-common repo in a file
        called overcloud_containers.yaml.j2.
        We don't intervene in that part, and it will be tested with the rest.
        But container-push now allows for this list to match against a grep
        pattern file in a fixed position. We create such file during staging
        setup So the list of containers effectively considered will be reduced.
        """
        image_names = self.config['containers']['images-suffix']
        pattern_file_path = self.config['containers']['pattern_file_path']
        self.config['results']['pattern_file_path'] = pattern_file_path

        if self.config['dry-run']:
            return

        with open(pattern_file_path, "w") as pattern_file:
            for image_name in image_names:
                line = ("^{}$\n".format(image_name))
                pattern_file.write(line)

    def teardown_registries(self, results):
        for registry_conf in results['targets'] + [results['source']]:
            registry = Registry(registry_conf['name'])
            registry.stop()

