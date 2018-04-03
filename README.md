# Stocky
This is a web-based program for stock taking using a bluetooth-connected RFID reader. Currently, the only RFID reader device supported is the [Technology Solutions 1128 Bluetooth Reader](https://www.tsl.com/products/1128-bluetooth-handheld-uhf-rfid-reader/).

## Architectural Overview
From the user perspective, Stocky is designed as a web application -- the user starts a browser
and connects to a server running on the same machine. The Bluetooth reader must be paired
to the same machine.

From a developer perspective, Stocky consists of a server application that talks to the RFID reader
and the webclient (javascript code) running in the browser.
Both server and client code is written in python 3.6, with the webclient being transpiled into
javascript with the [Transcrypt transpiler](https://transcrypt.org/).

Client and server communicate via the websocket protocol which allows for bidirectional
data transfer to be initiated by either client or server.
The server is implemented using the light-weight [Flask](http://flask.pocoo.org/) web framework with
the [Flask-Sockets](https://github.com/kennethreitz/flask-sockets)
and [gevent-websocket](https://github.com/jgelens/gevent-websocket)  extensions.

All of the server and webclient code is designed to be compiled and run within a docker container.

## Quick Start
1. **Prerequisites:** In order to build and compile Stocky, you will need a (linux) computer with the following installed:
  1. docker
  2. the GNU make program
  3. a web browser such as firefox.

2. **Build the docker image:** Once you have copied the source code from github, perform
     a `cd stockygit/stocky-devel`.
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
    To build the docker container, issue a `make build` command.

3. **Configure the Stocky application**

4. **Run Stocky in its docker container**

