"""
This file contains classes and functionto interact with containers registries
"""
import datetime
import logging
import os
import pprint
import re
import subprocess

from common import PromotionError


class RegistryClient(object):

    log = logging.getLogger("promoter")

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
        # for docker.io we need special treatment for each request, we get the
        # token, then we pass it with every request.
        auth_url = "https://auth.docker.io/token?service=registry.docker.io&scope" \
                   "=repository:{}:push,pull"


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

    def repo_rename(self, repo=None, components=None, replace={},
                    parts=['registry', 'namespace','repo', 'tag']):
        ''' Deconstructs a repo name and reconstructrs following rules
            part of a name can be selectivley included or replaced
        '''
        if repo is None and components is None:
            raise TypeError("No repo and no components specified")

        if components is None:
            components = self.get_containers_components(repo)

        components.update(replace)
        full_name = ""
        for part in parts:
            if part not in components:
                self.log.error("repo_rename: Invalid part '{}'", part)
                continue
            if part == 'registry':
                if components['registry'] is None:
                    components['registry'] = ""
                else:
                    components['registry'] += "/"

            elif part == 'tag':
                if components['tag'] is  None:
                    components['tag'] = ""
                else:
                    components['tag'] = ":" + components['tag']
            elif part == 'namespace':
                if components['namespace'] is  None:
                    components['namespace'] = ""
                else:
                    components['namespace'] += "/"

            full_name += components[part]


        return full_name

    def get_containers_components(self, full_name):
        ''' The regex fails in some corner cases:
            "localhost:6000/nova" (rare)
            "nova" (not rare locally)
            Both need special cases
        '''
        container_regex = "(\w*:[0-9]{,5})?/?([\w-]*)?/?([\w-]*):+([\w][\w.-]{0,127})?"
        # TODO(gcerami) For case 1 we should count the  / in the name, if we
        # have only one we are in the special case
        # For case 2 search for a / in the full_name
        if "/" not in full_name:
            components = (None, None, full_name, None )
        else:
            components = re.search(container_regex, full_name).groups()
            # create a dictionary with the components name as keys
            components = dict(zip(("registry", "namespace", "repo", "tag"),
                                  components))

        return components

    def containers_filter(self, containers, filters):
        ''' filters is a sictionary of field:regex to apply to container
        '''
        filtered_containers = []

        # If there are no filters, everything matches
        if not filters:
            return containers

        for full_name in containers:
            components = self.get_containers_components(full_name)

            res = []
            for key, value in filters.items():
                res.append(bool(re.search(value, components[key])))
            if all(res) and res is not []:
                filtered_containers.append(full_name)

        return filtered_containers

    def local_retag(self, src_repos, dest_tag=None, src_registry=None):
        ''' The input to this method is assumed to be from internal data structures
            in form of a list of name:tags, not from a actual image listing
            src_registry is a dict with all info on registry
        '''
        retagged_repos = []

        if isinstance(src_repos, str):
            src_repos = [src_repos]

        # Images may have been build locally without registry suffix
        src_suffix = ""
        # Or may have already been tagged with a registry suffix
        if src_registry is not None:
            src_suffix = "/".format(src_registry['host'])

        for src_repo in src_repos:
            src_name = self.repo_rename(src_repo, replace={"registry": src_registry['host']})
            source_image = self.client.images.get(src_name)
            src_tag = self.get_containers_components(src_repo)['tag']
            parts = {"registry": self.host}
            dest_name = self.repo_rename(src_repo, replace=parts, parts=['registry', 'namespace', 'repo'])
            # Every image must have a tag, if tag is None then reuse the source tag
            if dest_tag == None:
                dest_tag = src_tag
            source_image.tag(dest_name, dest_tag)
            retagged_repos.append((dest_name, dest_tag))

        return retagged_repos

    def remote_retag(self, repos, old_tag, new_tag):
        if isinstance(repos, str):
            repos = [repos]
        for repo in repos:
            manifest = self.manifest_get(repo, old_tag)
            self.manifest_post(manifest, repo, new_tag)

    def local_remove(self, repos):
        if isinstance(repos, str):
            repos = [repos]

        for repo_name in repos:
            try:
                name = "{}/{}".format(self.host, repo_name)
                self.client.images.remove(name, force=True)
            except docker.errors.ImageNotFound:
                pass

    def repo_pull(self, src_repos, filters={}):
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
        if not (self.manifest_exists(repo, tag) and
                self.manifest_exists(repo, other_tag)):
            return False

        manifest = self.manifest_get(repo, tag)
        other_manifest = self.manifest_get(repo, other_tag)

        return (manifest['config']['digest'] ==
                other_manifest['config']['digest'])

    def validate_containers(self, dlrn_hash, containers_list, name=None,
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
        for repo in containers_list:
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
            results['hash_valid'] = True

        return results


class RegistriesClient(object):
    """
    This class interacts with containers registries
    """

    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        self.git_root = self.config.git_root
        self.logfile = os.path.abspath(os.path.join(
            self.git_root,
            "../promoter_logs/container-push/%s.log" %
            datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
        self.promote_playbook = os.path.join(self.git_root,
                                             'ci-scripts',
                                             'container-push',
                                             'container-push.yml')
        self.push_opts = ("-e manifest_push=%s -e target_registries_push=%s"
                          "" % (self.config.manifest_push,
                                self.config.target_registries_push))

        env = os.environ
        env['RELEASE'] = self.config.release
        env['SCRIPT_ROOT'] = self.git_root
        env['DISTRO_NAME'] = self.config.distro_name
        env['DISTRO_VERSION'] = self.config.distro_version
        self.promote_env = env

    def promote(self, candidate_hash, target_label, **kwargs):
        """
        This method promotes containers whose tag is equal to the dlrn_id
        specified by retagging them with the target_label.
        Currently invokes an external ansible playbook for the effective
        promotion
        :param candidate_hash:  The hash to select container tags
        :param target_label: the new tag to apply to the containers
        :param kwarg: unused
        :return: None
        """

        self.log.info("Containers promote '{}' to {}: Attempting promotion"
                      "".format(candidate_hash, target_label))

        self.promote_env['PROMOTE_NAME'] = target_label
        self.promote_env['COMMIT_HASH'] = candidate_hash.commit_hash
        self.promote_env['DISTRO_HASH'] = candidate_hash.distro_hash
        self.promote_env['FULL_HASH'] = candidate_hash.full_hash
        # Use single string to make it easy to copy/paste from logs
        cmd = (
            "env "
            "ANSIBLE_LOG_PATH=%s"
            "RELEASE=%s "
            "COMMIT_HASH=%s "
            "DISTRO_HASH=%s "
            "FULL_HASH=%s "
            "PROMOTE_NAME=%s "
            "SCRIPT_ROOT=%s "
            "DISTRO_NAME=%s "
            "DISTRO_VERSION=%s "
            "ANSIBLE_DEBUG=False "
            "ansible-playbook -v %s %s" % (
                self.logfile,
                self.config.release,
                candidate_hash.commit_hash,
                candidate_hash.distro_hash,
                candidate_hash.full_hash,
                target_label,
                self.git_root,
                self.config.distro_name,
                self.config.distro_version,
                self.push_opts,
                self.promote_playbook
            )
        )
        # Remove color codes from ansible output
        ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
        try:
            self.log.info('Running: %s', cmd)
            container_logs = subprocess.check_output(cmd.split(" "),
                                                     stderr=subprocess.STDOUT)
            # containers_log needs decoding in python3
            if type(container_logs) is not str:
                container_logs = container_logs.decode()
            self.log.info("Containers promote '{}' to {}: Successful promotion"
                          "".format(candidate_hash, target_label))
            self.log.info("Containers promote '{}' to {}: Successful promotion "
                          "start logs -----------------------------"
                          "".format(candidate_hash, target_label))
            # for line in container_logs.split("\n"):
            #     self.log.info(ansi_escape.sub('', line))
            self.log.info("Containers promote '{}' to {}: Successful promotion "
                          "end logs -----------------------------"
                          "".format(candidate_hash, target_label))
        except subprocess.CalledProcessError as ex:
            self.log.error("Containers promote '{}' to {}: Failed promotion"
                           "".format(candidate_hash, target_label))
            self.log.error("Containers promote '{}' to {}: Failed promotion"
                           "start logs -----------------------------"
                           "".format(candidate_hash, target_label))
            for line in ex.output.decode("UTF-8").split("\n"):
                self.log.error(ansi_escape.sub('', line))
            self.log.exception(ex)
            self.log.error("Containers promote '{}' to {}: Failed promotion end"
                           " logs -----------------------------"
                           "".format(candidate_hash, target_label))
            raise PromotionError("Failed to promote overcloud images")
