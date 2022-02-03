"""
A Python Script to check for current-tripleo dlrn md5 is synced on all
upstream cloud or not.

For running: $python3 mirror_sync_status.py

"""
import posixpath

import click
import requests

# Target Mirrors generated using get_all_upstream_mirrors.py script
target_mirrors = [
    "http://mirror02.regionone.linaro-us.opendev.org",
    "http://mirror.regionone.linaro-us.opendev.org",
    "http://mirror02.mtl01.inap.opendev.org",
    "http://mirror.mtl01.inap.opendev.org",
    "http://mirror02.iad3.inmotion.opendev.org",
    "http://mirror.iad3.inmotion.opendev.org",
    "http://mirror02.gra1.ovh.opendev.org",
    "http://mirror.gra1.ovh.opendev.org",
    "http://mirror01.sjc1.vexxhost.opendev.org",
    "http://mirror.sjc1.vexxhost.opendev.org",
    "http://mirror01.regionone.osuosl.opendev.org",
    "http://mirror.regionone.osuosl.opendev.org",
    "http://mirror01.regionone.limestone.opendev.org",
    "http://mirror.regionone.limestone.opendev.org",
    "http://mirror01.ord.rax.opendev.org",
    "http://mirror.ord.rax.opendev.org",
    "http://mirror01-int.ord.rax.opendev.org",
    "http://mirror-int.ord.rax.opendev.org",
    "http://mirror01.kna1.airship-citycloud.opendev.org",
    "http://mirror.kna1.airship-citycloud.opendev.org",
    "http://mirror01.iad.rax.opendev.org",
    "http://mirror.iad.rax.opendev.org",
    "http://mirror01-int.iad.rax.opendev.org",
    "http://mirror-int.iad.rax.opendev.org",
    "http://mirror01.dfw.rax.opendev.org",
    "http://mirror.dfw.rax.opendev.org",
    "http://mirror01-int.dfw.rax.opendev.org",
    "http://mirror-int.dfw.rax.opendev.org",
    "http://mirror01.ca-ymq-1.vexxhost.opendev.org",
    "http://mirror.ca-ymq-1.vexxhost.opendev.org",
    "http://mirror01.bhs1.ovh.opendev.org",
    "http://mirror.bhs1.ovh.opendev.org",
]

# OpenStack releases
releases = ["master", "wallaby", "victoria", "ussuri", "train"]

# RDO port slug
rdo_content_port_slug = "8080/rdo"

# CentOS Package Compose
centos_compose = "https://composes.centos.org/latest-CentOS-Stream-8/COMPOSE_ID"

# CentOS Mirror slug
centos_slug = "centos/8-stream/COMPOSE_ID"

# Get CentOS compose ID


def get_centos_compose_id(compose_url=centos_compose):
    """
    Get CentOS compose ID
    """
    return requests.get(compose_url).text


def construct_centos_mirror(mirror, centos_slug=centos_slug):
    """
    Construct the CentOS proxy mirror
    """
    return posixpath.join(mirror, centos_slug)


def generate_rdo_slug(distro, release, promotion_name="current-tripleo"):
    """
    slug: <distroname+distroversion>-release/promotion_name
    """
    return posixpath.join("-".join([distro, release]), promotion_name)


# Get dlrn md5 hash
def get_delorean_md5_hash(
        rdo_slug,
        rdo_source="https://trunk.rdoproject.org",
        dlrn_md5="delorean.repo.md5"):
    """
    Retrive the delorean md5 hash
    """
    dlrn_md5_url = posixpath.join(rdo_source, rdo_slug, dlrn_md5)
    return requests.get(dlrn_md5_url).text


# Construct RDO mirror url
def construct_rdo_proxy_mirror_url(mirror):
    """
    Construct url <mirror>:8080/rdo
    """
    return ":".join([mirror, rdo_content_port_slug])


# Construct DLRN MD5 hash url
def construct_dlrn_md5_hash_url(md5_hash):
    """
    Return DLRN md5 hash generated URL
    """
    return "{}/{}/{}".format(md5_hash[:2], md5_hash[2:4], md5_hash)


# Construct full proxy url
def get_rdo_proxy_url(mirror, distro, release, md5_hash):
    """
    Return full rdo mirror proxy url
    """
    rdo_proxy_url = construct_rdo_proxy_mirror_url(mirror)
    rdo_slug = generate_rdo_slug(distro, release)
    dlrn_md5_url = construct_dlrn_md5_hash_url(md5_hash)
    return posixpath.join(
        rdo_proxy_url,
        rdo_slug,
        dlrn_md5_url,
        "delorean.repo.md5")


# Verify content over proxy mirror
def verify_content(content_url, compare_content):
    """
    It verifies the content from source (rdo/centos) to proxy mirror url.
    """
    try:
        proxy_content = requests.get(content_url, timeout=5)
        if compare_content == proxy_content.text:
            return "synced"
        else:
            return "not synced"
    except requests.exceptions.RequestException:
        return "Not found"


# Run RDO Mirror sync verification
def run_rdo_sync(distro, release):
    rdo_slug = generate_rdo_slug(distro, release)
    md5_sum = get_delorean_md5_hash(rdo_slug)
    print(f"Expected Hash to be present: {md5_sum}")
    print(f"=== Performing verification for {release} ===")
    for mirror in target_mirrors:
        rdo_proxy_url = get_rdo_proxy_url(mirror, distro, release, md5_sum)
        print()
        print("{} -> {}".format(mirror, verify_content(rdo_proxy_url, md5_sum)))


# Run CentOS mirror sync verification
def run_centos_sync():
    compose_id = get_centos_compose_id()
    print(f"Expected Compose ID to be present: {compose_id}")
    print("=== Performing verification ===")
    for mirror in target_mirrors:
        mirror_proxy_url = construct_centos_mirror(mirror)
        print()
        print("{} -> {}".format(mirror,
                                verify_content(mirror_proxy_url,
                                               compose_id)))


@click.command()
@click.option("--release", default="master", help="This is OpenStack Release")
@click.option(
    "--distro", default="centos8", help="This is Distribution Name and version"
)
@click.option("--all", is_flag=True, help="Print mirror sync for all releases")
@click.option(
    "--centos", is_flag=True, help="Print mirror sync status for CentOS Stream"
)
def main(distro=None, release=None, all=False, centos=False):
    if all:
        for openstack_release in releases:
            run_rdo_sync(distro, openstack_release)
    elif centos:
        run_centos_sync()
    else:
        run_rdo_sync(distro, release)


# Get the status of all mirrors
if __name__ == "__main__":
    main()
