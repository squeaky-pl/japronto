#!/bin/bash

set -ex

if [[ $JAPR_WHEEL == "1" ]]; then
  if [[ $JAPR_OS == "Linux" ]]; then
    docker run --rm -w /io -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 /opt/python/cp35-cp35m/bin/python setup.py bdist_wheel
    docker run --rm -w /io -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 /opt/python/cp36-cp36m/bin/python setup.py bdist_wheel
    docker run --rm -w /io -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 auditwheel repair dist/*-cp35-cp35m-linux_x86_64.whl
    docker run --rm -w /io -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 auditwheel repair dist/*-cp36-cp36m-linux_x86_64.whl
    rm dist/*.whl
    ls -lha wheelhouse
    unzip -l wheelhouse/*.whl
    cp wheelhouse/*.whl dist
  fi

  if [[ $JAPR_OS == "Darwin" ]]; then
    python setup.py bdist_wheel
    ls -lha dist
    unzip -l dist/*.whl
  fi

  twine upload -u squeaky dist/*.whl
fi
