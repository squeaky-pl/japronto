#!/bin/bash

export JAPR_MSG=`git show -s --format=%B | xargs`
export JAPR_WHEEL=`[[ $JAPR_MSG == *"[travis-wheel]"* ]] && echo 1 || echo 0`
export JAPR_OS=`uname`

if [[ $VERSION == "3.5."* ]]; then
  export PYTHON_TAG=cp35-cp35m
elif [[ $VERSION == "3.6."* ]]; then
  export PYTHON_TAG=cp36-cp36m
elif [[ $VERSION == "3.7."* ]]; then
  export PYTHON_TAG=cp37-cp37m
fi

env | grep "^JAPR_"
