import logging

from common import DlrnHash, DlrnClient, RegistryClient, QcowClient
from transaction import PromoterTransaction

class PromoterAgent(object):

    log = logging.getLogger('promoter')

    def __init__(self, config):
        self.config = config
        print(self.config)
        self.dlrn_client = DlrnClient(self.config)
        self.registry_client = RegistryClient(self.config)

    def get_containers_list(self, dlrn_hash, patterns=None):
        versions_reader = self.dlrn_client.get_versions(dlrn_hash)
        ooo_common_commit = None
        for row in versions_reader:
            if row[0] == "openstack-tripleo-common":
                ooo_common_commit = row[2]
                break

        if ooo_common_commit is None:
            raise Exception("unable to find tripleo common commit hash")

        containers_url = ("{}/{}/raw/commit/{}/{}"
                          "".format(self.openstack_repo_url,
                                    ooo_common_project,
                                    ooo_common_commit,
                                    overcloud_containres_path))

        containers_content = urllib2.urlopen(containers_url).read()

        full_list = re.findall(self.config.ooo_filter_regex, containers_content)
        if self.config.ooo_custom_pattern is not None:
            full_list = list(set(full_list).intersection(self.config.ooo_custom_pattern))

        return full_list


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

        containers = self.get_containers_list(dlrn_hash)
        results['containers'] = self.registry_client.validate_containers(dlrn_hash, containers, name=name)

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

    def end_transaction(self):
        self.transaction = None
