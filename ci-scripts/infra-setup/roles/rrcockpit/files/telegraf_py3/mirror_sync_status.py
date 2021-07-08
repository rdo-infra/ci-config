"""
A Python Script to check for current-tripleo dlrn md5 is synced on all upstream cloud or not.

For running: $python3 mirror_sync_status.py

"""
import posixpath
import requests
from urllib.parse import urljoin

# Source Mirror
RDO_SOURCE_CONTENT = "https://trunk.rdoproject.org/centos8-master/current-tripleo/delorean.repo.md5"

# Target Mirrors
RDO_TARGET_MIRRORS = [
    "http://mirror.bhs1.ovh.opendev.org",
    "http://mirror.gra1.ovh.opendev.org",
    "http://mirror.mtl01.inap.opendev.org",
    "http://mirror01.ca-ymq-1.vexxhost.opendev.org",
    "http://mirror01.dfw.rax.opendev.org",
    "http://mirror01.iad.rax.opendev.org",
    "http://mirror01.ord.rax.opendev.org",
    "http://mirror01.regionone.limestone.opendev.org",
    "http://mirror01.regionone.linaro-us.opendev.org",
    "http://mirror01.regionone.osuosl.opendev.org",
    "http://mirror01.sjc1.vexxhost.opendev.org",
    "http://mirror02.iad3.inmotion.opendev.org",
    "http://mirror02.regionone.linaro-us.opendev.org",
    "http://mirror02.us-west-1.packethost.openstack.org",
]

# RDO content port
RDO_CONTENT_PORT = "8080"

# RDO URL slug
RDO_URL_SLUG = "rdo/centos8/current-tripleo"

# Get dlrn md5 hash
def get_delorean_md5_hash(RDO_SOURCE_CONTENT):
    """
    Retrive the delorean md5 hash
    """
    return requests.get(RDO_SOURCE_CONTENT).text

# Construct RDO mirror url
def construct_rdo_proxy_mirror_url(mirror):
    """
    Construct url <mirror>:RDO_CONTENT_PORT/RDO_URL_SLUG
    """
    base_proxy_url = ':'.join([mirror, RDO_CONTENT_PORT])
    return urljoin(base_proxy_url, RDO_URL_SLUG) 

# Construct DLRN MD5 hash url
def construct_dlrn_md5_hash_url(md5_hash):
    """
    Return DLRN md5 hash generated URL
    """
    return "{}/{}/{}".format(md5_hash[:2],
                             md5_hash[2:4],
                             md5_hash)

# Construct full proxy url
def get_rdo_proxy_url(mirror, md5_hash):
    """
    Return full rdo mirror proxy url
    """
    rdo_proxy_url = construct_rdo_proxy_mirror_url(mirror)
    dlrn_md5_url = construct_dlrn_md5_hash_url(md5_hash)
    return posixpath.join(rdo_proxy_url,
                          dlrn_md5_url,
                          "delorean.repo.md5")

# Verify DLRN MD5 content over proxy mirror
def verify_dlrn_md5(rdo_proxy_full_url, trunk_md5_sum):
    """
    It verifies the content from RDO trunk repo to RDO proxy mirror url
    """
    try:
        proxy_md5_hash = requests.get(rdo_proxy_full_url)
        if trunk_md5_sum == proxy_md5_hash.text:
            return "synced"
        else:
            return "not synced"
    except requests.exceptions.RequestException as e:
        return "Not found"

# Get the status of all mirrors
if __name__ == "__main__":
    trunk_md5_sum = get_delorean_md5_hash(RDO_SOURCE_CONTENT)
    for mirror in RDO_TARGET_MIRRORS:
        proxy_mirror_url = get_rdo_proxy_url(mirror, trunk_md5_sum)
        print()
        print("{} -> {}".format(mirror, 
                                verify_dlrn_md5(proxy_mirror_url,trunk_md5_sum)))