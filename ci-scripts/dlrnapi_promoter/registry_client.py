from containers_lists import ImageList
from docker_clients import DockerRegistryApiClient


class ImagesLists(object):

    def __init__(self):

        self.lists = []

    self.candidate_hash = None
    self.target_label = None
    self.to_upload = None
    self.to_promote = None
    self.to_download = None
    self.promoted = None
    self.downloaded = None
    self.uploaded = None
    self.status = None

    def create_images_list(self, tag, images=None, name=None):
        images_list = ImageList(self.registry, self.namespace, tag,
                                images=images)
        if name is not None:
            setattr(self, name, images_list)
        return images_list



class RegistryClient(object):

    def __init__(self, config, allow_status_check=False,
                 api_client_class=DockerRegistryApiClient):
        self.config = config
        self.allow_status_check = allow_status_check
        self.api_client = api_client_class(config)
        self.namespace = config['namespace']
        self.host = config['host']
        self.port = config['port']
        self.registry = "{}:{}".format(self.host, self.port)
        self.driver = config['driver']
        self.lists = ImagesLists()
        self.base_names = None

    def set_promotion_parameters(self, base_names, candidate_hash,
                                 target_label):
        self.base_names = base_names
        self.candidate_hash = candidate_hash
        self.target_label = target_label

    def cleanup(self):
        for list_name in self.lists.lists:
            images_list = getattr(self.lists, list_name)
            images_list.local_remove()


class TargetRegistryClient(RegistryClient):

    def __init__(self):
        pass

    def set_promotion_parameters(self, base_names, candidate_hash,
                                 target_label):
        super(TargetRegistryClient, self).set_promotion_parameters(
            base_names, candidate_hash, target_label)
        self.create_images_list(candidate_hash.full_hash, name="uploaded",
                                images=self.base_names)
        self.create_images_list(candidate_hash.full_hash, name="promoted")
        if self.allow_status_check:
            self.check_status()
        else:
            self.to_upload.add_images(base_names)
            self.to_download.add_images(base_names)
            self.to_promote.add_images(base_names)

    def check_status(self):
        # check for images:dlrn_hash that are not in target registry and
        # for images that are different from images:target_label (meaning
        # they were not promoted to target_label)
        # check images tagged with hash, compare digests with same images
        # with target_label as tag
        status = self.uploaded.check_images_status(
            locally=False,
            remotely=True,
            compare_tag=self.target_label)

        self.to_upload.add_images(status['missing_remotely'])
        self.to_promote.add_images(status['digest_mismatch'])

    def upload_images(self, downloaded):
        downloaded.reassign(self.registry, self.namespace, locally=True,
                            remotely=False)
        uploaded_images = self.to_upload.push(remove_from_list=True)
        self.create_images_list(self.candidate_hash.full_hash,
                                name="uploaded",
                                images=uploaded_images)


class SourceRegistryClient(RegistryClient):

    def set_promotion_parameters(self, base_names, candidate_hash,
                                 target_label):
        super(SourceRegistryClient, self).set_promotion_parameters(
            base_names, candidate_hash, target_label)
        self.create_images_list(candidate_hash.full_hash, name="to_promote")
        self.create_images_list(candidate_hash.full_hash, name="to_check")
        self.create_images_list(candidate_hash.full_hash, name="to_download")

    def check_status(self):
        status = self.to_download.check_images_status(
            remotely=True,
            compare_tag=self.target_label)
        if status['missing_remotely'].search('_x86_64'):
            raise Exception("Missing images in source registry")

        self.to_download.add_images(status['missing_locally'])
        self.to_download_optional.add_images(status['missing_locally_optional'])
        self.to_promote.add_images(status['digest_mismatch'])

    def download_images(self):
        downloaded_images = self.to_download.pull(remove_from_list=True)
        self.create_images_list(self.candidate_hash.full_hash,
                                name="downloaded",
                                images=downloaded_images)
        return self.downloaded

    def promote_images(self):
        promoted_images = self.to_promote.retag(self.target_label,
                                                locally=False, remotely=True)
        self.create_images_list(self.candidate_hash.full_hash,
                                name="promoted",
                                images=promoted_images)

    def validate_promotion(self):
        return self.promoted == self.expected

