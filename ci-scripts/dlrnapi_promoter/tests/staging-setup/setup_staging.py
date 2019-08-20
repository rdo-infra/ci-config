from dlrn import db as dlrn_db
from dlrn import utils
import datetime
import docker
import yaml
import os
import pprint


def get_hash(commit, distro):
    return "{}_{}".format(commit, distro[:8])

IMAGES_HOME="/tmp/"
#IMAGES_HOME=os.environ.get('HOME', "/tmp")
FIXTURE_FILE="fixtures/scenario-1.yaml"

with open(FIXTURE_FILE) as ff:
    fixture = yaml.safe_load(ff)

date = datetime.datetime.now()
container_suffix = date.strftime("-%Y%m%d-%H%M%S-%f")
print(container_suffix)

for commit in fixture["commits"]:
    dlrn_hash = get_hash(commit["commit_hash"], commit["distro_hash"])


# Generate Images hieradchy
image_dir = IMAGES_HOME/"centos7/stein/rdo_trunk" + dlrn_hash)
#IMAGES_HOME/"redhat8/master/rdo_trunk")
os.symlink = IMAGE_HOME + "ciccio" + "previous-ciccio"
symlink_dir = IMAGE_HOME + "ciccio" + "promotionname"
os.makdirs(image_dir)

image_file = dlrn_hash
with open(image_file, 'a'):
    pass


# Containers
client = docker.from_env()

for image in images:
    image = client.image.pull()
    tag = image_name:new_tag
    image.tag(name, tag)
    image.push(image_new_tag)

generate_containers_file
containers_list = "\n".join(containers)
with open(containers_file) as cf:
    cf.write(containers_list)


clenup

#get_registry_data()
curl -v -X DELETE http://registryhost:reigstryport/v2/${docker_image_name}/manifests/${digest}




# Dlrn staging
#
repo_path = /tmp/delorean

session = dlrn_db.getSession("sqlite:///%s" % filepath)
utils.loadYAML(session, 'fixtures/scenario-1.yaml')

os.mkdir(repo_path + dlrn_hash)
os.symlink(repo_path + dlrn_hash, candidate_name)


