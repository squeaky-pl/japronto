#!/bin/bash

export JAPR_MSG=`git show -s --format=%B | xargs`
export JAPR_WHEEL=`[[ $JAPR_MSG == *"[travis-wheel]"* ]] && echo 1 || echo 0`
export JAPR_OS=`uname`
env | grep "^JAPR_"
