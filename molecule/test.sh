#!/bin/bash

#
# This file run molecule unit jobs
#

for i in `ls molecule/unit`; do
    molecule test -s $i
done
