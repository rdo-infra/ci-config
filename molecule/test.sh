#!/bin/bash

#
# This file run molecule unit jobs
#

if [ $# -gt 1 ] 
then
  molecule test -s $1
else
  for i in `ls molecule/unit`; do
      molecule test -s $i
  done
fi
