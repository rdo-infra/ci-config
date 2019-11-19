import base64
import csv
import dlrnapi_client
import docker
import json
import logging
import os
import paramiko
import requests
import time
import urllib

try:
    import urllib2 as url
except:
    import urllib.request as url

def str2bool(value):
    if value in ['yes', 'true', 'True', 'on', '1']:
        return True
    return False


class DlrnClientError(Exception):
    pass

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
        default_openstack_repo_url = "{}://{}/{}".format(self.openstack_repo_scheme,
                                                         self.openstack_repo_host,
                                                         self.openstack_repo_root)
        self.openstack_repo_url = config['main'].get("openstack_repo_url", default_openstack_repo_url)

        # In test you can set scheme to file, host to  "" and root to /path/
        self.dlrn_repo_host = config['main'].get('repo_host', "trunk.rdoproject.org")
        self.dlrn_repo_root = config['main'].get('repo_root', "")
        self.dlrn_repo_scheme = config['main'].get('repo_scheme', "https")
        self.dlrn_username = config['main']['dlrn_username']
        self.dlrn_password = config['main']['dlrn_password']
        default_repo_url = "{}://{}/{}".format(self.dlrn_repo_scheme,
                                               self.dlrn_repo_host,
                                               self.dlrn_repo_root,
                                               self.distro,
                                               self.release)

        self.dlrn_repo_url = config['main'].get('dlrn_repo_url', default_repo_url)

        self.ooo_common_project = "openstack/tripleo-common"
        self.ooo_containers_path = "container-images/overcloud_containers.yaml.j2"
        self.ooo_filter_regex = "(?<=name_prefix\}\}).*(?=\{\{name_suffix)"
        self.ooo_custom_pattern = None
        containers_custom_filter_file = config['main'].get('containers_pattern_file',
                                                           None)

        # FIXME: This is policy and it shouldn't be here. Promotion
        # configuration file should pass their server preference as variable
        default_qcow_server = 'rdo'
        if 'rhel' in self.distro or 'redhat' in self.distro:
            default_qcow_server = 'private'

        self.qcow_server = config['main'].get('qcow_server', default_qcow_server)

        default_qcow_servers = {
            "rdo": {
                "host": "images.rdoproject.org",
                "user": "uploader",
                "root": "/var/www/html/images/"
            },
            "private": {
                "host": "38.145.34.141",
                "root": "/var/www/rcm-guest/images/",
                "user": "centos",
            }
        }
        self.qcow_servers = config['main'].get('qcow_servers', default_qcow_servers)

        self.registries = config['main']['registries']
        self.qcow_images = sorted([
            "ironic-python-agent.tar",
            "ironic-python-agent.tar.md5",
            "overcloud-full.tar",
            "overcloud-full.tar.md5",
            "undercloud.qcow2",
            "undercloud.qcow2.md5",
        ])

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

    def __init__(self, commit=None, distro=None, from_api=None, from_dict=None):
        self.commit_hash = ""
        self.distro_hash = ""
        if from_api is not None:
            try:
                self.log.debug("Using values from a Promotion object")
                self.commit_hash = from_api.commit_hash
                self.distro_hash = from_api.distro_hash
            except AttributeError:
                raise AttributeError("Cannot create hash,"
                                     " invalid source API object")
        elif from_dict is not None:
            try:
                self.log.debug("Using values from a Promotion object")
                self.commit_hash = from_dict['commit_hash']
                self.distro_hash = from_dict['distro_hash']
            except KeyError:
                raise KeyError("Cannot create hash:"
                               " invalid source dict")

        else:
            self.commit_hash = commit
            self.distro_hash = distro

    def __eq__(self, other):
        if not hasattr(other, 'commit_hash') or \
            not hasattr(other,'distro_hash'):
             raise TypeError("One of the objects is not a valid DlrnHash")

        return (self.commit_hash == other.commit_hash and self.distro_hash == other.distro_hash)

    def __ne__(self, other):
        if not hasattr(other, 'commit_hash') or \
            not hasattr(other,'distro_hash'):
             raise TypeError("One of the objects is not a valid DlrnHash")

        return (self.commit_hash != other.commit_hash or self.distro_hash != other.distro_hash)

    def __str__(self):
        return "commit: %s, distro: %s" % (self.commit_hash, self.distro_hash)

    def __repr__(self):
        return "<DlrnHash object commit: %s, distro: %s>" % (self.commit_hash, self.distro_hash)

    @property
    def full_hash(self):
        return '{0}_{1}'.format(self.commit_hash, self.distro_hash[:8])

    @property
    def short_hash(self):
        return '{0}_{1}'.format(self.commit_hash[:8], self.distro_hash[:8])

    @property
    def repo_path(self):
        url = "{}/{}/{}".format(self.commit_hash[:2],
                                self.commit_hash[2:4],
                                self.full_hash)
        return url


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
        dlrnapi_client.configuration.password = self.config.dlrn_password
        dlrnapi_client.configuration.username = self.config.dlrn_username
        api_client = dlrnapi_client.ApiClient(host=self.config.api_url)
        self.api_instance = dlrnapi_client.DefaultApi(api_client=api_client)
        self.log.info('Using API URL: %s', api_client.host)
        self.last_promotions = {}

    def get_versions(self, dlrn_hash):
        versions_url = ("{}/{}/versions.csv"
                        "".format(self.config.dlrn_repo_url,
                                  dlrn_hash.repo_path))
        self.log.info("Accessing versions at %s", versions_url)
        try:
            versions_file = url.urlopen(versions_url)
            versions_reader = csv.reader(versions_file)
            return versions_reader
        except url.URLError:
            raise DlrnClientError("Unable to fetch package versions file")

    def validate_hash(self, dlrn_hash, name=None):
        ''' This method verifies if a hash is present in the server
            if name is passed, it also verifies that the name points
            to that hash
        '''
        results = {
            "hash_valid": False,
            "promotion_valid": False
        }
        jobs = self.fetch_jobs(dlrn_hash)
        if jobs is not None:
            results['hash_valid'] = True

        if name is not None:
            pointed_hash = self.fetch_hash(name)
            if pointed_hash is not None and pointed_hash == dlrn_hash:
                results['promotion_valid'] = True

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
        api_response = sorted(api_response, key=lambda x:x.timestamp, reverse=True)
        try:
            return DlrnHash(from_api=api_response[0])
        except IndexError:
            return None

    def fetch_jobs(self, dlrn_hash, success=None):
        '''Fetch the successfully finished jobs for a specific DLRN hash
           return None in case of errors
           returns empty list if no votes yet
        '''
        self.jobs_params.commit_hash = dlrn_hash.commit_hash
        self.jobs_params.distro_hash = dlrn_hash.distro_hash
        if success is not None:
            self.jobs_params.success = str(success)

        try:
            api_response = self.api_instance.api_repo_status_get(self.jobs_params)
        except dlrnapi_client.rest.ApiException:
            self.log.error('Exception when calling api_repo_status_get: %s',
                           dlrnapi_client.rest.ApiException)
            return None

        return api_response

    def promote_hash(self, dlrn_hash, promote_name):
        '''Promotes a set of hash values as a named link using DLRN API'''
        params = dlrnapi_client.Promotion()
        params.commit_hash = dlrn_hash.commit_hash
        params.distro_hash = dlrn_hash.distro_hash
        params.promote_name = promote_name


        # wait al least one second before promoting the same name
        # or promotions will have the same timestamp in dlrn
        try:
            time_now = time.time()
            time_since = time_now - self.last_promotions[promote_name]
            if time_since < 1.0:
                delay = 1.0 - time_since
                time.sleep(delay)
        except KeyError:
            pass

        try:
            res = self.api_instance.api_promote_post(params)
        except dlrnapi_client.rest.ApiException:
            self.log.error('Exception when calling api_promote_post: %s',
                           dlrnapi_client.rest.ApiException)
            raise DlrnClientError

        self.last_promotions[promote_name] = time.time()

        # Runtime check if we have promoted correctly
        promoted_hash = self.fetch_hash(promote_name)
        if promoted_hash != dlrn_hash:
            raise DlrnClientError("Dlrn hash {} was not promoted correctly"
                                  " to {}. It still points to {}"
                                  "".format(dlrn_hash, promote_name, promoted_hash))

        self.log.info("%s promoted to %s", dlrn_hash, promote_name)

class RegistryClient(object):

    def __init__(self, config):
        self.name = config['name']
        self.host = config['host']
        self.username = config['username']
        self.password = config['password']
        self.api_url = config['api_url']
        auth_data = {
            "username": self.username,
            "password": self.password,
            "email": "",
            "serveraddress": "self.host"
        }
        # X-Rgistry-Auth header to be passed to all post operations
        auth_json = json.dumps(auth_data).encode('ascii')
        x_registry_auth = base64.urlsafe_b64encode(auth_json)
        self.raw_api_headers = {
            "X-Registry-Auth": x_registry_auth,
            "Content-Type": "application/json",
        }
        self.client = docker.from_env()
        self.client.login(self.username, self.password,
                         registry=self.host,
                         reauth=True)


    def manifest_exists(self, repo, tag):
        session = requests.Session()
        url = "{}/{}/manifests/{}".format(self.api_url, repo, tag)
        session.headers.update(self.raw_api_headers)
        res = session.head(url, verify=False, auth=(self.username, self.password))
        if not res.ok:
            return False
        return True

    def manifest_get(self, repo, tag):
        session = requests.Session()
        session.headers.update(self.raw_api_headers)
        session.headers['Accept'] = "application/vnd.docker.distribution.manifest.v2+json"
        url = "{}/{}/manifests/{}".format(self.api_url, repo, tag)
        res = session.get(url, verify=False, auth=(self.username, self.password))

        if not res.ok:
            return {}

        return json.loads(res.text)

    def manifest_post(self, manifest, repo, tag):
        session = requests.Session()
        session.headers.update(self.raw_api_headers)
        url = "{}/{}/manifests/{}".format(self.api_url, repo, tag)
        res = session.post(url, data=manifest, verify=False, auth=(self.username, self.password))

        if not res.ok:
            raise Exception("OMG")

    def local_retag(self, src_repo, src_tag, dest_tag, src_registry=""):
        if isinstance(src_repo, str):
            repos = [src_repo]
        for repo in repos:
            source_name = "{}/{}:{}".format(src_registry, repo, src_tag)
            source_image = self.client.get(repo, tag)
            source_image.tag(repo, new_tag)

    def remote_retag(self, repo, old_tag, new_tag):
        manifest = self.manifest_get(repo, old_tag)
        self.manifest_post(manifest, repo, new_tag)

    def repo_push(self, repo, tag):
        repo = self.client.image.get(repo)
        self.client.image.push(repo)

    def tag_compare(self, repo, tag, other_tag):
        if not (self.manifest_exists(repo, tag) and
                self.manifest_exists(repo, other_tag)):
            return False

        manifest = self.manifest_get(repo, tag)
        other_manifest = self.manifest_get(repo, other_tag)

        return (manifest['config']['digest'] ==
                other_manifest['config']['digest'])

    def validate_containers(self, dlrn_hash, containers_list, namespace, name=None):
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
            "containers_missing": containers_list,
            "containers_present": [],
            "comparisons": {},
            "promotion_valid": name is not None,
        }

        count = 0
        for container_name in containers_list:
            repo = "{}/{}".format(namespace, container_name)
            if self.manifest_exists(repo, dlrn_hash.full_hash):
                count += 1
                results['containers_present'].append(repo)
                results['containers_missing'].remove(repo)
            if name is not None:
                res = self.tag_compare(repo, dlrn_hash.full_hash, name)
                if not res:
                    results['promotion_valid'] = False
                results['comparison'][container_name] = res


        if count == len(containers_list):
            results['containers_valid'] = True

        return results

class QcowClient(object):

    def __init__(self, config):
        self.config = config
        server_conf = config.qcow_servers[config.qcow_server]
        self.user = server_conf['user']
        self.root = server_conf['root']
        self.host = server_conf['host']
        if self.host == "localhost":
            self.user = None

        self.images_dir = os.path.join(self.root, config.distro,
                                       config.release, "rdo_trunk")

        client = paramiko.SSHClient()
        client.load_system_host_keys()


        client.connect(self.host, username=self.user)
        self.client = client.open_sftp()
        self.client.chdir(self.root)

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
            "hash_valid": False,
            "promotion_valid": False,
            "qcow_valid": False,
            "missing_qcows": self.config.qcow_images,
            "present_qcows": [],
        }

        try:
            images_path = os.path.join(self.images_dir, dlrn_hash.full_hash)
            stat = self.client.stat(images_path)
            results['hash_valid'] = True
            images = sorted(self.client.listdir(images_path))
            results['present_qcows'] = images
            results['missing_qcows'] = \
                list(set(self.config.qcow_images).difference(images))
            if images == self.config.qcow_images:
                results['qcow_valid'] = True
        except IOError:
            pass

        if name is not None:
            try:
                link = self.client.readlink(name)
                if link == dlrn_hash.full_hash:
                    results['promotion_valid'] = True
            except IOError:
                pass

        return results
