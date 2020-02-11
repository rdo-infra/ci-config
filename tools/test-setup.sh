#!/bin/bash
set -euxo pipefail
# Used by Zuul CI to perform extra bootstrapping

# Bumping system tox because version from CentOS 7 is too old
# We are not using pip --user due to few bugs in tox role which does not allow
# us to override how is called. Once these are addressed we will switch back
# non-sudo mode.
PYTHON=$(command -v python3 python | head -n1)

sudo "$PYTHON" -m pip install -U tox six "zipp<0.6.0;python_version=='2.7'"
# removal of old command needed because upgrade may not rewrite it, breaking it in some cases
sudo rm -f /usr/local/bin/tox
sudo "$PYTHON" -m pip install --force-reinstall -U tox
