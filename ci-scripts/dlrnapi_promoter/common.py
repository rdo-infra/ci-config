import dlrnapi_client
import logging
import paramiko
import urllib

class Config(object):

    def __init__(self, config):
        self._config = kwargs

    def promotion_checkpoint(self):
        checkpoint = {}
        checkpoint

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
        self.api_client = dlrnapi_client.ApiClient(host=config['api_url'])
        self.api_instance = dlrnapi_client.DefaultApi(api_client=self.api_client)
        self.log.info('Using API URL: %s', self.api_client.host)

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

    def validate_containers(self, dlrn_hash, name=None):
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

    def login(self):
        self.paramiko.login(self.host)

    def logout(self):
        self.paramiko.logout(self.host)

    def link(self, dlrn_hash, name):
        self.symlink

    def get_previous_hash(self, name):
        try:
            qcowclient = QcowClient()
            image_dir = qcowclient.readlink("previous" + promote_name)
        except NoLink:
            pass
        previous_hash = image_dir

        return previous_hash

    def validate_qcows(self, hash, name):
        # Check we have the images dir in the server
        # if name is specified, verify that name points to the hash
        # - maybe qcow ran and failed
        # Check at which point of qcow promotion we stopped
        # 1) did we create a new symlink ?
        # 2) did we create the previous symlink ?
        try:
            image_dir = get_server_dir(hash)
            qcow_verified = True
        except:
            pass


