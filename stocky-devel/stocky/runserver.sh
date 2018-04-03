#!/bin/bash

# start the flask server with our stocky.py application

# Can set this to set default logging mode for flask -- or can use the logging.yaml file instead
# export FLASK_DEBUG=1

# NOTE: this is for the the version WITHOUT flask-socket (deprecated)
# python -m flask run --host=0.0.0.0

# build the javascript of the client...
# (cd webclient; make webclient)

gunicorn -k flask_sockets.worker "stocky:init_app('serverconfig.yaml')" --bind 0.0.0.0:5000
