# cico-node-done-from-ansible.sh
# A script that releases nodes from a SSID file written by
SSID_FILE=${SSID_FILE:-$WORKSPACE/cico-ssid}

for ssid in $(cat ${SSID_FILE}); do
    #cico -q node done $ssid
    curl -v http://admin.ci.centos.org:8080/Node/fail?key=$CICO_API_KEY&ssid=$ssid
done
