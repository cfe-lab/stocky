# Stocky
This is a web-based program for stock taking using a bluetooth-connected RFID reader. Currently, the only RFID reader device supported is the [Technology Solutions 1128 Bluetooth Reader](https://www.tsl.com/products/1128-bluetooth-handheld-uhf-rfid-reader/).

## Architectural Overview
From the user perspective, Stocky is designed as a web application -- the user starts a browser
and connects to a server running on the same machine. The Bluetooth reader must be paired
to the same machine.

From a developer perspective, Stocky consists of a server application that talks to the RFID reader
and the webclient (javascript code) running in the browser.
Server **and** client code is written in python 3.6, with the webclient being transpiled into
javascript with the [Transcrypt transpiler](https://transcrypt.org/).

Client and server communicate via the websocket protocol which allows for bidirectional
data transfer to be initiated by either client or server.
The server is implemented using the light-weight [Flask](http://flask.pocoo.org/) web framework with
the [Flask-Sockets](https://github.com/kennethreitz/flask-sockets)
and [gevent-websocket](https://github.com/jgelens/gevent-websocket)  extensions.

All of the server and webclient code is designed to be compiled and run within a docker container.

## Quick Start
1. **Prerequisites:** In order to build and compile Stocky, you will need a (linux) computer with the following installed:
  - docker
  - a web browser such as firefox.
  - the GNU make program


  The above requirements are sufficient for deploying the program without change.
  Note that the requirement for make is not strict, as the required commands in the Makefile could
  be extracted from it and issued directly.
  If you wish to develop the project, i.e. edit the source code and see the effect of
  these changes, then some further system requirements must be met.
  See section [Code Development](#code-development) for more details.

2. **Build the docker image:** Once you have copied the source code from github
     - perform a `cd stockygit/stocky-devel/stocky/static`.
 	   The stocky server loads an image called `lablogo.png` from this directory.
	   A `sample_logo.png` file is provided if you have none yourself:
	   ```
	   cp sample_logo.png  lablogo.png
	   ```
	 - cd into `stockygit/stocky-devel`: `cd ../../`
	   This directory contains a Makefile. Run `make` to get a menu of options:
   ```
   Available targets:
   help:     This Makefile can be used to build and run the stocky docker images.
   build:    build the docker image for stocky
   build-nocache: build the docker image for stocky from scratch
   runlocal: run the stocky docker image interactively with bash.
   runprod:  run the stocky docker image for production.
   clean-logs: remove all log files from the stocky-devel-state directory
   ```
   To build the docker container, issue a `make build` command. This will result in
   a docker image tagged with `stocky-base`.

3. **Configure the Stocky application**
   Still in the `stockygit/stocky-devel` directory, make two directories that stocky
   will access when running. These directories will be mounted by the docker container
   when it launches (see the Makefile for details of how this is done):
   ```
   mkdir stocky-devel-config; mkdir stocky-devel-state
   ```
   The two sample configuration files in the current directory must now be copied into
   stocky-devel-config, renamed and appropriately changed to reflect your requirements:
   ```
   cp logging_sample.yaml stocky-devel-config/logging.yaml
   cp serverconfig_sample.yaml stocky-devel-config/serverconfig.yaml
   ```
   Now edit these two files to your taste.
   - `logging.yaml` controls how the server logs events to its log file in
      the `stocky-devel-state` directory. Changing entries in this
      file can be useful for code development, but it can initially be left alone.
   - `serverconfig.yaml` contains many hardware specific entries such as the 
      Bluetooth imac address of your RFID reader etc. and will certainly need to be 
	  modified before proceeding. Comments in the sample file contain instructions for
	  how to determine the required parameters on a linux machine.

4. **Run Stocky in its docker container**
   To launch the stocky server, again use the Makefile provided:
   ```
   make runprod
   ```
   will launch the docker container built in step 1, and start the web server which will
   be listening on port 5000. To access the server, point your web browser to http://localhost:5000 .
   
   To stop this container, use the `docker ps` command to find its container id, and
   issue a `docker kill ID_number` to stop it.

## Code Development 
   The container launched with `make runprod` runs the stocky source code that was loaded into
   the docker image at **image build time** - that means any subsequent changes in the stocky
   directory will not be reflected in the running container.
   For development work, rebuilding the docker image after every source code change would
   be tedious.
   
   For code development, we instead, launch the docker image interactively and mount the
   local stocky source code into the running container. This is what the `make runlocal` target
   achieves.
   In this use case, the developer is responsible for
   - compiling the webclient into javascript when required
   - starting or restarting the webserver if/when required
   
