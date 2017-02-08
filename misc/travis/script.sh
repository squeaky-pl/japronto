#!/bin/bash

set -ex

if [[ $JAPR_WHEEL == "1" ]]; then
  if [[ $JAPR_OS == "Linux" ]]; then
    for PYTHON_TAG in "cp35-cp35m cp36-cp36m"; do
      docker run --rm -u `id -u` -w /io -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 /opt/python/$PYTHON_TAG/bin/python setup.py bdist_wheel
      docker run --rm -u `id -u` -w /io -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 auditwheel repair dist/*-$PYTHON_TAG-linux_x86_64.whl
      unzip -l wheelhouse/*-$PYTHON_TAG-manylinux1_x86_64.whl
    done
    rm -f dist/*
    cp wheelhouse/*.whl dist
  fi

  if [[ $JAPR_OS == "Darwin" ]]; then
    python setup.py bdist_wheel
    ls -lha dist
    unzip -l dist/*.whl
  fi

  twine upload -u squeaky dist/*.whl
fi
