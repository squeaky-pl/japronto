#!/bin/bash

cd ~

sudo apt-get update
sudo apt-get install -y python3 git libbz2-dev libz-dev libsqlite3-dev libssl-dev gcc make libffi-dev lcov
git clone https://github.com/yyuu/pyenv .pyenv
.pyenv/bin/pyenv install -v 3.6.0
wget https://pypi.python.org/packages/d4/0c/9840c08189e030873387a73b90ada981885010dd9aea134d6de30cd24cb8/virtualenv-15.1.0.tar.gz
tar xvfz virtualenv-15.1.0.tar.gz
python3 virtualenv-15.1.0/virtualenv.py -p .pyenv/versions/3.6.0/bin/python japronto-env
git clone https://github.com/squeaky-pl/japronto

cd japronto/src/picohttpparser
./build
cd -

cd japronto
../japronto-env/bin/pip install -r requirements.txt
../japronto-env/bin/python build.py
cd -

git clone https://github.com/wg/wrk
cd wrk
make
cd -

cp wrk/wrk japronto
