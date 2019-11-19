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


class PromoterAgent(object):

    log = logging.getLogger('promoter')

    def __init__(self, config):
        self.config = config
        self.dry_run = config['dry_run']
        self.distro = config['distro']
        self.release = config['release']
        self.api_url = config['api_url']
        self.promote_name = config['promote_name']

        self.dlrn_client = DlrnClient(self.config)
        self.registry_client = RegistryClient(self.config)

    def get_previous_hash(promote_name):
        # Are we getting the previous hash from the qcow
        # or from dlrnapi ?
        previous_hash = None
        qcow_client.get_previous_hash()

        try:
            hashes = dlrnapi.promotion_get(promote_name)
            index = hashes.find(rollback_hash)
            previous_hash = hashes[index - 1]
        except NotFound:
            pass

        return previous_hash

    def enqueue_operation(op, args):
        operation['action'] = action
        operation['args'] = args
        self.operations.append(operation)

    def promote():
        # rollback all resources in parallel
        threads = {}
        for op in self.operations:
            target = getattr(self, op['action'])
            args = op['args']
            thread[action] = threading.Thread(target=target, args=args)
            thread[action].start()

        for op in operations:
            action, args = op
            thread[action].join()

        for op in operations:
            action, args = op
            if action == "qcow" and self.rolled_back_links < 2:
                self.log.error("Qcow rollback failed")
            elif action == "containers" and self.rolled_back_containers < len(containers):
                self.log.error("Containers rollback failed")


    def validate_promotion(self, dlrn_hash, name=None):
        # We need to check if it's sane to rollback to
        # the specified hash, checking if all the images are
        # present before rolling back.

        # Check hash is present in dlrnapi

        # if name is specified, verify that name points to the hash
        results = {
            "hash": None,
            "qcows": None,
            "containers": None,
        }

        results['hash'] = self.dlrn_client.validate_hash(dlrn_hash, name=name)

        results['containers'] = self.registry_client.validate_containers(dlrn_hash, name=name)

        results['qcow'] = self.qcow_client.alidate_qcows(hash, name=name)

        if not results['hash']:
            promotion_verified = False

        items_missing = {
            "containers": containers_missing,
            "qcows": qcows_missing,
        }

        return promotion_verified, item_missing

    def tag_containers(self, containers, rollback_hash, promote_name):
        registry = Registry(host)
        namespace = "tripleo" + release

        self.rolled_back_containers = 0
        for container in containers:
            repo = namespace + container
            registry.retag(repo, rollback_hash, promote_name)
            self.rolled_back_containers += 1


    def tag_qcow_images(self, new_hashes):
        image_client = QcowClient(config)

        self.rolled_back_links = 0
        image_client.login()
        image_client.relink(rollback_hash, promote_name)
        self.rolled_back_links += 1
        if previous_hash:
            image_client.relink(previous_hash, "previous" + promote_name)
            self.rolled_back_links += 1
        image_client.logout()

    def start_transaction(self, attempt_hash, current_hash, name):
        self.transaction = PromoterTransaction(self)
        self.transaction.start(attempt_hash, current_hash, name)
        return self.transaction

class PromoterTransaction(object):

    log = logging.getLogger('promoter')

    def __init__(self, promoter_agent):
        self.promoter_agent = promoter_agent

        # marks = None means we never started a transaction
        self.rollback_items = None


    def start(self, attempt_hash, current_hash, name):
        ''' This method marks the checkpoint for a transaction
            having a checkpoint is optional, but would greatly
            help in rolling back.
        '''
        self.attempted_hash = attempt_hash
        self.rollback_hash_name = name
        self.rollback_hash = current_hash
        self.rollback_items = {
            "containers": None,
            "qcow": None
        }

    def end(self):
        self.rollback_items = None
        self.rollback_hash = None
        self.rollback_hash_name = None
        self.attempted_hash = None


    def checkpoint(self, mark, progress):
        ''' Promoter can use this method to mark the state of
            advancement of a promotion critical section
        '''
        if progress == "start":
            self.rollback_items[mark] = "check"
        else:
            self.rollback_items[mark] = "full"


    def rollback(self, attempted_hash=None, rollback_hash=None, name=None):

        # First thing we need a hash.
        # if we are in a transaction we can use the recorded hash
        # The attempted has is the one that supposedly failed

        if rollback_hash is None:
            try:
                rollback_hash = self.rollback_hash
            except AttributeError:
                self.log.error("This rollabck is not running during a transaction and no rollback hash was specified, please specify an hash to rollback to")
                raise

        if name is None:
            try:
                name = self.rollback_hash_name
            except AttributeError:
                self.log.error("This rollabck is not running during a transaction and no name was specified, please specify the promotion name to rollback")
                raise

        # if we have a specific hash taht filed, we can try to understand what succeded and rollback only taht
        if attempted_hash is None:
            try:
                # We have a specific hash tht failed
                attempted_hash =  self.attempted_hash
            except AttributeError:
                self.log.warning("Not in a transaction and no failed hash specified: the rollback function will nto n able to optimize the rollbackl and will have to redo the complete promotion")


        # Check if we can roll back to this hash.
        results = self.promoter_agent.validate_promotion(rollback_hash)
        if results['promotion_valid'] is False:
           self.log("Can't roll back to the specified hash: missing pieces")

        promote_items = {
            "qcow": "all",
            "containers": "all",
        }


        if self.rollback_items is not None:
            _, items = validate_hash(attempted_hash, items=rollback_items)
            # if validation  report promotion succeded, don't do anything.
            if results['hash']['name_points_hash'] == True:
                # Name already points to hash
                self.log.info("Attempted hash is fully promoted, not rolling back")
                return
            promote_items = complete_items

        self.agent.promote(proote_items)

def parse_args():
    # We can pass directly the .ini file from the promoter
    # To get these infos
    distro = config['distro']
    release = config['release']
    api_url = config['api_url']

    # These must be provided
    promote_name = config['promote_name']
    rollback_hash # need to check validity, we can't roll back, to a hash if it's too old.


    # Optional, but useful
    failed_hash
    # Print warning
    # Without a failed hash, the only way to roll back is to
    # repromote everything to the rollback_hash
    return {}

if __name__ == "__main__":
    # rollback running as standalone tool
    config = parse_args()
    # Print Warning
    warning = ("This tool is about to roll back promotion to a know"
               "good state. If you are calling this tool by hand, you should ensure that no other"
               "promotion process is disbled, as this tool doesn't syncronize with any active promotion process"
               "and can't lock the resources it's about to modify. Please type 'yes' if you want to continue")
    if not args.skip_warning:
        print(warning)
    agent = PromoterAgent(config=config)
    transaction = agent.start_transaction()
    transaction.perform_rollback(config['hash'])
