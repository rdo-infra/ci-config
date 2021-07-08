"""
A Python Script to check for current-tripleo dlrn md5 is synced on all
upstream cloud or not.

For running: $python3 mirror_sync_status.py

"""
import posixpath

import click
import requests

# Target Mirrors generated using get_all_upstream_mirrors.py script
rdo_target_mirrors = [
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


def generate_rdo_slug(distro, release, promotion_name="current-tripleo"):
    """
    slug: <distroname+distroversion>-release/promotion_name
    """
    return posixpath.join("-".join([distro, release]), promotion_name)


# Get dlrn md5 hash
def get_delorean_md5_hash(
    rdo_slug, rdo_source="https://trunk.rdoproject.org", dlrn_md5="delorean.repo.md5"
):
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
    return posixpath.join(rdo_proxy_url, rdo_slug, dlrn_md5_url, "delorean.repo.md5")


# Verify DLRN MD5 content over proxy mirror
def verify_dlrn_md5(rdo_proxy_full_url, trunk_md5_sum):
    """
    It verifies the content from RDO trunk repo to RDO proxy mirror url
    """
    try:
        proxy_md5_hash = requests.get(rdo_proxy_full_url, timeout=5)
        if trunk_md5_sum == proxy_md5_hash.text:
            return "synced"
        else:
            return "not synced"
    except requests.exceptions.RequestException:
        return "Not found"


# Run Mirror sync verification
def run_sync(distro, release):
    rdo_slug = generate_rdo_slug(distro, release)
    md5_sum = get_delorean_md5_hash(rdo_slug)
    print(f"Expected Hash to be present: {md5_sum}")
    print(f"=== Performing verification for {release} ===")
    for mirror in rdo_target_mirrors:
        rdo_proxy_url = get_rdo_proxy_url(mirror, distro, release, md5_sum)
        print()
        print("{} -> {}".format(mirror, verify_dlrn_md5(rdo_proxy_url, md5_sum)))


@click.command()
@click.option("--release", default="master", help="This is OpenStack Release")
@click.option(
    "--distro", default="centos8", help="This is Distribution Name and version"
)
@click.option("--all", is_flag=True, help="Print mirror sync for all releases")
def main(distro=None, release=None, all=False):
    if all:
        for openstack_release in releases:
            run_sync(distro, openstack_release)
    else:
        run_sync(distro, release)


# Get the status of all mirrors
if __name__ == "__main__":
    main()
