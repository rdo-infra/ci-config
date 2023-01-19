#!/bin/bash

#
# This file run molecule unit jobs
#

if [ $# -gt 1 ]; then
    molecule test -s $1 || exit 1
else
    for i in `ls molecule/`; do
        if [[ $i == system_* ]]; then
            molecule test -s $i || exit 1
        fi
    done
fi
