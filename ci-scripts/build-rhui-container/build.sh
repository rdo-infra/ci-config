#!/bin/bash
set -exuo pipefail
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd $DIR

# fail if we are not authenticated
docker login trunk.registry.rdoproject.org

# build
docker build --pull -t rhel8-rhui-testing .

# tag
docker tag rhel8-rhui-testing  trunk.registry.rdoproject.org/rhel/rhel8-rhui-testing:latest

# push
docker -l debug push trunk.registry.rdoproject.org/rhel/rhel8-rhui-testing

# enjoy a beer