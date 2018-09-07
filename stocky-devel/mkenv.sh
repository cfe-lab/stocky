#!/bin/bash


virtualenv -p /usr/local/bin/python3 env

source env/bin/activate

pip3 install --upgrade pip

#NOTE: pep8 is deprecated, flake8 uses pycodestyle instead
# pip3 install pep8 flake8

pip3 install flake8
pip3 install transcrypt



