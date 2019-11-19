import logging
try:
    import urllib2 as url
except ImportError:
    import urllib.request as url

import re

from common import DlrnHash, DlrnClient, RegistryClient, QcowClient
from transaction import PromoterTransaction

class PromoterAgent(object):

    log = logging.getLogger('promoter')

    def __init__(self, config):
        self.config = config
        self.namespace = "tripleo{}".format(self.config.release)
        self.dlrn_client = DlrnClient(self.config)
        self.target_registries = {}
        for registry_config in self.config.registries['targets']:
            registry_client = RegistryClient(registry_config)
            self.target_registries[registry_config['name']] = registry_client

        self.qcow_client = QcowClient(self.config)

    def get_containers_list(self, dlrn_hash, patterns=None):
        versions_reader = self.dlrn_client.get_versions(dlrn_hash)
        ooo_common_commit = None
        for row in versions_reader:
            if row and row[0] == "openstack-tripleo-common":
                ooo_common_commit = row[2]
                break

        if ooo_common_commit is None:
            raise Exception("unable to find tripleo common commit hash")

        containers_url = ("{}/{}/raw/commit/{}/{}"
                          "".format(self.config.openstack_repo_url,
                                    self.config.ooo_common_project,
                                    ooo_common_commit,
                                    self.config.ooo_containers_path))

        containers_content = url.urlopen(containers_url).read()

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

    def rollback(self, attempted_hash, rollback_hash, name):
        pass

    def promote(self, dlrn_hash, name):
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


    def validate_hash(self, dlrn_hash, name=None, steps=['dlrn', 'qcows', 'containers']):
        # We need to check if it's sane to rollback to
        # the specified hash, checking if all the images are
        # present before rolling back.

        # Check hash is present in dlrnapi

        # if name is specified, verify that name points to the hash
        results = {
            "hash_valid": False,
            "promotion_valid": name is not None,
            "dlrn": None,
            "qcows": None,
            "containers": None,
            "registries": {},
        }

        hash_validations = []
        promotion_validations = []
        if 'dlrn' in steps:
            results['dlrn'] = self.dlrn_client.validate_hash(dlrn_hash, name=name)

        if 'qcows' in steps:
            results['qcows'] = self.qcow_client.validate_qcows(dlrn_hash, name=name)

        containers = self.get_containers_list(dlrn_hash)

        if 'containers' in steps:
            results['containers'] = {}
            registries_hash_valid = []
            registries_promotion_valid = []
            for registry_name, registry_client in self.target_registries.items():
                results['registries'][registry_name] = \
                    registry_client.validate_containers(dlrn_hash,
                                                        containers,
                                                        self.namespace,
                                                        name=name)

                valid = results['registries'][registry_name]['hash_valid']
                registries_hash_valid.append(valid)
                valid = results['registries'][registry_name]['promotion_valid']
                registries_promotion_valid.append(valid)
            results['containers']['hash_valid'] = all(registries_hash_valid)
            results['containers']['promotion_valid'] = all(registries_promotion_valid)

        for step in steps:
            valid = results[step]['promotion_valid']
            promotion_validations.append(valid)
            valid = results[step]['hash_valid']
            hash_validations.append(valid)

        results['hash_valid'] = all(hash_validations)
        results['promotion_valid'] = all(promotion_validations)

        return results

    def analyze_results(self, results, dlrn_hash, name):
        analyzed_results = {
            "missing": {
                "hash": None,
                "hash_promotion": None,
                "containers_promotion": None,
                "containers_hash": None,
                "images_hash": None,
                "images_promotion": None,
            },
            "completed":{
                "hash": None,
                "hash_promotion": None,
                "containers_promotion": None,
                "containers_hash": None,
                "images_hash": None,
                "images_promotion": None,
            }
        }
        return analyzed_results

    def push_containers(self, containers, dlrn_hash, exclude_registries=None):
        for registries in self.target_registries:
            pass

    def retag_containers(self, containers, old_tag, new_tag, exclude_registries=None):
        for registry in self.target_registries:
            for container in containers:
                repo = "{}/{}".format(self.namespace, container)
            registry.remote_retag(repo, old_tag, new_tag)

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
