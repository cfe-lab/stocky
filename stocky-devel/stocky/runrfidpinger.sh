#!/bin/bash

# -- NOTE: run this script from WITHIN the running docker container.

# Start the flask server with our stocky.py application
# Can set this to set default logging mode for flask -- or can use the logging.yaml file instead
export FLASK_DEBUG=1

# build the javascript of the client...
# (cd webclient; make webclient)

# this is the insecure version (insecure http, ws protocols)
gunicorn -k flask_sockets.worker "stocky:app" --bind 0.0.0.0:5000

# this is the secure version: https, wss protocols
# gunicorn --certfile /stockyconfig/cert.pem --keyfile /stockyconfig/key.pem -k flask_sockets.worker "stocky:app" --bind 0.0.0.0:5000


