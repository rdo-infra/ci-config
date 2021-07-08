"""
Python Script to fetch all the AFS mirrors from
https://opendev.org/opendev/system-config/src/branch/master/inventory/service/host_vars

Any file name stating with mirror, is a mirror file and it contains the list of mirrors
"""
import os
import subprocess

import yaml

# Clone system config repo
def clone_repo(git_repo_url, clone_dir="/tmp"):
    """
    Clone a particular repo to /tmp directory
    """
    repo_path = os.path.join(clone_dir, os.path.basename(git_repo_url))
    if not os.path.isdir(repo_path):
        os.chdir(clone_dir)
        cmd = ["git", "clone", git_repo_url]
        subprocess.run(cmd, capture_output=True)
    return repo_path


# Get mirror info from system-config
def get_mirror_info(mirror_file_name):
    """
    Extract mirror info a file
    """
    with open(mirror_file_name) as f:
        data = yaml.load(f, yaml.FullLoader)
    mirror_list = data["letsencrypt_certs"]
    mirror_key = (
        os.path.basename(mirror_file_name)
        .replace(".opendev.org.yaml", ".main")
        .replace(".", "-")
    )
    return mirror_list[mirror_key]


# Get all mirrors
def get_all_mirrors(system_config_git_url, system_config_mirror_path):
    """
    Returns a list of mirrors
    """
    mirrors = []
    mirror_dir = os.path.join(
        clone_repo(system_config_git_url), system_config_mirror_path
    )
    mirror_files = [
        os.path.join(mirror_dir, file)
        for file in os.listdir(mirror_dir)
        if file.startswith("mirror")
    ]
    for mirror in mirror_files:
        mirrors.extend(get_mirror_info(mirror))
    return mirrors


if __name__ == "__main__":
    system_config_git_url = "https://opendev.org/opendev/system-config"
    system_config_mirror_path = "inventory/service/host_vars"
    mirrors = get_all_mirrors(system_config_git_url, system_config_mirror_path)
    mirrors = ["http://{}".format(mirror) for mirror in mirrors]
    print(mirrors)
