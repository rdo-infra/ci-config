import csv
import dlrnapi_client
import logging
import paramiko

try:
    from urllib2 import urlopen
except:
    from urllib.request import urlopen

def str2bool(value):
    if value in ['yes', 'true', 'True', 'on', '1']:
        return True
    return False

class PromoterConfig(object):

    log = logging.getLogger("promoter")

    def __init__(self, config):
        # Promoter run specific config
        self.distroname =  config['main']['distro_name'].lower()
        self.distroversion = config['main']['distro_version']
        self.distro = "{}{}".format(self.distroname, self.distroversion)
        self.release = config['main']['release']
        self.api_url = config['main']['api_url']
        self.dry_run = str2bool(config['main']['dry_run'])

        # These should be in promoter general config
        self.openstack_repo_host = config['main'].get('openstack_repo_host',
                                                      "opendev.org")
        self.openstack_repo_scheme = config['main'].get('openstack_repo_scheme',
                                                        'https')
        self.openstack_repo_root = config['main'].get('openstack_repo_root',
                                                      "")
        self.openstack_repo_url = "{}://{}/{}".format(self.openstack_repo_scheme,
                                                      self.openstack_repo_host,
                                                      self.openstack_repo_root)

        # In test you can set scheme to file, host to  "" and root to /path/
        self.dlrn_repo_host = config['main'].get('repo_host', "trunk.rdoproject.org")
        self.dlrn_repo_root = config['main'].get('repo_root', "")
        self.dlrn_repo_scheme = config['main'].get('repo_scheme', "https")
        self.dlrn_repo_url = "{}://{}/{}".format(self.dlrn_repo_scheme,
                                                      self.dlrn_repo_host,
                                                      self.dlrn_repo_root)


        self.ooo_common_project = "openstack/tripleo-common"
        self.ooo_containers_path = "container-images/overcloud_containers.yaml.j2"
        self.ooo_filter_regex = "(?<=name_prefix\}\}).*(?=\{\{name_suffix)"
        self.ooo_custom_pattern = None
        containers_custom_filter_file = config['main'].get('containers_pattern_file',
                                                           None)
        try:
            with open(containers_custom_filter_file) as pf:
                custom_pattern = pf.read()
                self.ooo_custom_pattern = set(custom_pattern.split())
        except IOError:
            self.log.warning("Custom patter file not found")
        except TypeError:
            pass

        # Promotion specific config
        self.promote_name = None

class DlrnHash(dict):

    log = logging.getLogger("promoter")

    def __init__(self, commit=None, distro=None, source=None):
        if commit is None and distro is None and source is None:
            self.commit_hash = ""
            self.distro_hash = ""
        if source is not None:
            self.commit_hash = source.commit_hash
            self.distro_hash = source.distro_hash
            self.log.warning("Using values from source")
        else:
            self.commit_hash = commit
            self.distro_hash = distro

    def __eq__(self, other):
        return self.commit_hash == other.commit_hash and self.distro_hash == other.distro_hash

    def __str__(self):
        return "commit: %s, distro: %s" % (self.commit_hash, self.distro_hash)

    @property
    def full_hash(self):
        return '{0}_{1}'.format(self.commit_hash, self.distro_hash[:8])

    @property
    def short_hash(self):
        return '{0}_{1}'.format(self.commit_hash[:8], self.distro_hash[:8])

class DlrnClient(object):

    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        # This way of preparing parameters and configuration is copied
        # directly from dlrnapi CLI and ansible module
        self.hashes_params = dlrnapi_client.PromotionQuery()
        self.jobs_params = dlrnapi_client.Params2()
        self.promote_params = dlrnapi_client.Promotion()
        # TODO(gcerami): fix credentials gathering
        #dlrnapi_client.configuration.password = self.config.password
        #dlrnapi_client.configuration.username = self.config.username
        api_client = dlrnapi_client.ApiClient(host=self.config.api_url)
        self.api_instance = dlrnapi_client.DefaultApi(api_client=api_client)
        self.log.info('Using API URL: %s', api_client.host)

    def get_repo_path(self, dlrn_hash):
        url = "{}/{}/{}".format(dlrn_hash.commit_hash[:2],
                                dlrn_hash.commit_hash[2:2],
                                dlrn_hash.full_hash)
        return url

    def get_versions(self, dlrn_hash):
        repo_path = self.get_repo_path(dlrn_hash)
        versions_url = ("{}/{}-{}/{}/versions.csv"
                        "".format(self.config.dlrn_repo_url,
                                  self.config.distro,
                                  self.config.release,
                                  repo_path))
        self.log.info("Accessing versions at %s", versions_url)
        versions_file = urlopen(versions_url)
        versions_reader = csv.reader(versions_file)

        return versions_reader

    def validate_hash(self, dlrn_hash, name=None):
        ''' This method verifies if a hash is present in the server
            if name is passed, it also verifies that the name points
            to that hash
        '''
        results = {
            "hash_exists": False,
            "name_points_hash": False
        }
        jobs = self.fetch_jobs(dlrn_hash)
        if jobs is not None:
            results['hash_exists'] = True

        if name is not None:
            pointed_hash = self.fetch_hash(name)
            if pointed_hash == dlrn_hash:
                results['name_points_hash'] = True

        return results

    def fetch_hash(self, promote_name):
        self.hashes_params = dlrnapi_client.PromotionQuery()
        '''Get the commit and distro hashes for a specific promotion link'''
        self.hashes_params.promote_name = promote_name
        try:
            api_response = self.api_instance.api_promotions_get(self.hashes_params)
        except dlrnapi_client.rest.ApiException:
            self.log.error('Exception when calling api_promotions_get: %s',
                           dlrnapi_client.rest.ApiException)
            return None
        try:
            print(api_response[0])
            return DlrnHash(source=api_response[0])
        except IndexError:
            return None

    def fetch_jobs(self, dlrn_hash, success=None):
        '''Fetch the successfully finished jobs for a specific DLRN hash
           return None in case of errors
           returns empty list if no votes yet
        '''
        print(dlrn_hash)
        self.jobs_params.commit_hash = dlrn_hash.commit_hash
        self.jobs_params.distro_hash = dlrn_hash.distro_hash
        if success is not None:
            self.jobs_params.success = str(success)

        try:
            api_response = self.api_instance.api_repo_status_get(self.jobs_params)
        except dlrnapi_client.rest.ApiException:
            logger.error('Exception when calling api_repo_status_get: %s',
                         ApiException)
            return None

        return api_response

    def promote_hash(self, dlrn_hash, promote_name):
        '''Promotes a set of hash values as a named link using DLRN API'''
        params = dlrnapi_client.Promotion()
        params.commit_hash = dlrn_hash.commit_hash
        params.distro_hash = dlrn_hash.distro_hash
        params.promote_name = promote_name

        try:
            self.api_instance.api_promote_post(params)
            self.log.info("%s promoted to %s", dlrn_hash, promote_name)
        except dlrnapi_client.rest.ApiException:
            self.log.error('Exception when calling api_promote_post: %s',
                           dlrnapi_client.rest.ApiException)
            raise

class RegistryClient(object):

    def __init__(self, config):
        self.config = config

    def login(self):
        docker_client.login(self.username)
        self.token = token

    def remote_tag(self, repo, old_tag, new_tag):

        content_type="application/vnd.docker.distribution.manifest.v2+json"
        request = urlllin.add_header("Accept: {}".format(content_type))
        request = urlllin.add_header("Beared: {}".format(self.token))
        manifest = urllib.get("{}/v2/{}/manifests/{}".format(self.host, repo, old_tag))
        manifest.mangle()
        urllib.put("{}/v2/{}/manifests/{}".format(repo, new_tag), data=manifest)

    def validate_containers(self, dlrn_hash, containers_list, name=None):
        # Check we have all the containers we need to roll back to
        # if name is specified, verify that name points to the hash
        containers_missing = []
        for container in container_list:
            try:
                docker_client.get(container)
                cnt_count += 1
            except NotFound:
                containers_missing.append(container)

        if cnt_count == len(containers_list):
            containers_verified = True

            for name in images:
                images_toroll = set()
                try:
                    hash_manifest = docker_client.get(name, failed_hash)
                    try:
                        name_manifest = docker_client(image, promote_name)
                        if name_manifest.sha == image_manifeest.sha:
                            images_toroll.add(name_manifest)
                    except NotFound:
                        continue
                except Notfound:
                    continue

            if images_toroll:
                # We have containers retagged
                # roll them back
                rollback_items.append("container", container_toroll)

        return containers_verified, containers_missing

class QcowClient(object):

    def __init__(self, config):
        self.config = config
        self.user = "centos"
        self.root = "/var/www/html/images/"
        # This should be specified in the configuration file
        self.host = "images.rdoproject.org"
        if "rhel" in self.config['distro']:
            self.host = "38.145.34.141"
            self.root = "/var/www/rcm-guest/images/"

        self.images_dir = os.path.join(self.root,
                                       ''.join(config['distro']),
                                       config['release'], "rdo_trunk")

        client = paramiko.SSHClient()
        client.load_system_host_keys()

        # For testing
        self.host = "localhost"
        self.root = "/tmp/images"

        client.connect(self.config['images_server'])
        self.client = client.open_sftp()
        self.client.chdir(self.images_dir)

    def link(self, dlrn_hash, name):
        self.client.symlink(dlrn_hash, name)

    def promote(self, dlrn_hash, name, create_previous=False):
        try:
            current_hash = self.client.readlink(name)
        except IOError:
            pass

        self.link(dlrn_hash, name)

    def get_previous_hash(self, name):
        try:
            image_dir = self.client.readlink("previous" + promote_name)
        except IOError:
            pass
        previous_hash = image_dir

        return previous_hash

    def validate_qcows(self, dlrn_hash, name=None):
        # Check we have the images dir in the server
        # if name is specified, verify that name points to the hash
        # - maybe qcow ran and failed
        # Check at which point of qcow promotion we stopped
        # 1) did we create a new symlink ?
        # 2) did we create the previous symlink ?

        results = {
            "hash_exists": False,
            "name_points_hash": False,
            "qcow_present": False,
            "missing_qcows": "all",
            "present_qcows": []
        }

        try:
            self.client.stat('dlrn_hash')
            results['hash_exists'] = True
        except IOError:
            return results

        return results
