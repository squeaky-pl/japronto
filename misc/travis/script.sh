#!/bin/bash

set -ex

if [[ $JAPR_WHEEL == "1" ]]; then
  python setup.py bdist_wheel
  ls -lha dist
  unzip -l dist/*.whl
  twine upload -u squeaky dist/*.whl
fi
