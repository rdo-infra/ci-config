# Reads an installed file with DLRN metadata and returns the DLRN repository hash
# https://github.com/openstack-packages/DLRN/commit/147740c7648b34fd0395d7c5ba34a70fc6446b6c

function get_trunk_repository_hash() {
    local trunk_repository="${1:-http://buildlogs.centos.org/centos/7/cloud/x86_64/rdo-trunk-master}"
    local metadata_file="${2:-installed}"
    local metadata=$(curl -s "${trunk_repository}/${metadata_file}")
    local commit_hash=$(echo ${metadata} |cut -f2 -d " ")
    local distro_hash=$(echo ${metadata} |cut -f3 -d " ")
    local distro_short_hash=$(echo ${distro_hash} |cut -c -8)
    local trunk_hash="${commit_hash}_${distro_short_hash}"
    echo $trunk_hash
}
