#!/bin/bash

set -ex

if [[ $JAPR_OS == "Darwin" ]]; then
  export PATH=/Users/travis/build/squeaky-pl/japronto/venv/bin:$PATH
fi

if [[ $JAPR_WHEEL == "1" ]]; then
  if [[ $JAPR_OS == "Linux" ]]; then
    docker run --rm -u `id -u` -w /io -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 /opt/python/$PYTHON_TAG/bin/python setup.py bdist_wheel
    docker run --rm -u `id -u` -w /io -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 auditwheel repair dist/*-$PYTHON_TAG-linux_x86_64.whl
    rm -r dist/*
    cp wheelhouse/*.whl dist
  fi

  if [[ $JAPR_OS == "Darwin" ]]; then
    python setup.py bdist_wheel
  fi

  ls -lha dist
  unzip -l dist/*.whl
  twine upload -u squeaky dist/*.whl
fi
