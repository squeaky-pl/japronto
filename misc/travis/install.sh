#!/bin/bash

set -ex

if [[ $JAPR_OS == "Darwin" ]]; then
  source misc/terryfy/travis_tools.sh
  source misc/terryfy/library_installers.sh
  clean_builds
  get_python_environment macpython $VERSION venv
fi

if [[ $JAPR_WHEEL == "1" ]]; then
  pip install twine
fi
