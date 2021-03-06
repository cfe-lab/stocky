#!/bin/bash

# -- NOTE: run this script from WITHIN the running docker container.


# Start the flask server with our stocky.py application
# Can set this to set default logging mode for flask -- or can use the logging.yaml file instead
export FLASK_DEBUG=1

# build the javascript of the client...
# (cd webclient; make webclient)

gunicorn -k flask_sockets.worker "scan-test:init_app('./scantest-config.yaml')" --bind 0.0.0.0:5000
