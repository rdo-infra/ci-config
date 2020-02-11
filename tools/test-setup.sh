#!/bin/bash
set -euxo pipefail
# Used by Zuul CI to perform extra bootstrapping

# Bumping system tox because version from CentOS 7 is too old
# We are not using pip --user due to few bugs in tox role which does not allow
# us to override how is called. Once these are addressed we will switch back
# non-sudo mode.

# Hack for fixing broken combination of nodepool image and ensure-tox role.

PYTHON=$(command -v python3 python | head -n1)

# pre debug
$PYTHON -m virtualenv --version || true
$PYTHON -m tox --version || true
/usr/local/bin/tox --version  || true
$PYTHON -m pip --version || true
$PYTHON -m pip freeze

sudo rm -f /usr/local/bin/tox
sudo "$PYTHON" -m pip install "virtualenv<20.0" "tox>=3.14.3" tox-venv "zipp<0.6.0;python_version=='2.7'"

# post debug
$PYTHON --version
$PYTHON -m virtualenv --version
$PYTHON -m tox --version
/usr/local/bin/tox --version  # this needs to work for ensure-tox in particular
$PYTHON -m pip freeze
