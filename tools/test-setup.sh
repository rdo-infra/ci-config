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
$PYTHON -c 'import tox; print(tox.__file__)' || true
/usr/local/bin/tox --version  || true
$PYTHON -m pip --version || true
$PYTHON -m pip list # cannot use freeze as it may require sudo

# remove tox if it exists in user-libs, or it could be picked by python later
"$PYTHON" -m pip uninstall tox || true

sudo rm -f /usr/local/bin/tox
sudo "$PYTHON" -m pip install "six>=1.12" "tox>=3.14.3" tox-venv "zipp<0.6.0;python_version=='2.7'"

# post debug
$PYTHON --version
$PYTHON -m virtualenv --version
$PYTHON -m pip list
$PYTHON -c 'import tox; print(tox.__file__)' || true
$PYTHON -m tox --version
/usr/local/bin/tox --version  # this needs to work for ensure-tox in particular
