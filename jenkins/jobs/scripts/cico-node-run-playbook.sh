# Runs a specified playbook on all available hosts

WORKSPACE="${WORKSPACE:-/tmp}"
VENV="${WORKSPACE}/venv"

[[ ! -d "${VENV}" ]] && virtualenv "${VENV}"
source "${VENV}/bin/activate"

# Install requirements.
# Pin to version used by tripleo-quickstart as of this commit.
pip install ansible==2.5.8

# We keep connecting onto the same hosts that are continuously reinstalled
export ANSIBLE_HOST_KEY_CHECKING=False

# cico-get-node requests a duffy node and generates an ansible-compatible
# inventory at $WORKSPACE/hosts
ansible-playbook -i "${WORKSPACE}/hosts" "${WORKSPACE}/playbook.yml"
