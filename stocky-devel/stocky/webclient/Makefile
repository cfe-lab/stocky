# Use the Makefile in the docker image to create the webclient javascript code from the python code
# by using Transcrypt
shell := /bin/bash


LIBDIR = ../qailib

COMMON = ${LIBDIR}/common/base.py \
         ${LIBDIR}/common/serversocketbase.py \

LIBS =  ${LIBDIR}/transcryptlib/genutils.py \
  ${LIBDIR}/transcryptlib/htmlelements.py \
  ${LIBDIR}/transcryptlib/__init__.py \
  ${LIBDIR}/transcryptlib/serversocket.py \
  ${LIBDIR}/transcryptlib/SVGlib.py \
  ${LIBDIR}/transcryptlib/websocket.py \
  ${LIBDIR}/transcryptlib/widgets.py \
  ${LIBDIR}/transcryptlib/forms.py \
  ${LIBDIR}/transcryptlib/cleverlabels.py \
  ${LIBDIR}/transcryptlib/simpletable.py \
  commonmsg.py\
  wccontroller.py\
  wcstatus.py\
  wcviews.py\



# these are optios to the transcrypt transpiler
OPTS = -dc -ds -n -b -e6 -m -s sco_for_TS


default: help

# NOTE: this code taken from https://gist.github.com/rcmachado/af3db315e31383502660
help: ## Build and test the stocky webclient. Run this from within the running docker container.
	$(info Available targets:)
	@awk '/^[a-zA-Z\-\_0-9]+:/ {                                   \
          nb = sub( /^## /, "", helpMsg );                             \
          if(nb == 0) {                                                \
            helpMsg = $$0;                                             \
            nb = sub( /^[^:]*:.* ## /, "", helpMsg );                  \
          }                                                            \
          if (nb)                                                      \
            printf "\033[1;31m%-" width "s\033[0m %s\n", $$1, helpMsg; \
        }                                                              \
        { helpMsg = $$0 }'                                             \
        width=$$(grep -o '^[a-zA-Z_0-9]\+:' $(MAKEFILE_LIST) | wc -L)  \
	$(MAKEFILE_LIST)


# default: webclient

webclient: __target__/webclient.js ## compile the stocky web client (from python to javascript)

__target__/webclient.js: Makefile webclient.py  ${LIBS} ${COMMON}
	transcrypt ${OPTS} webclient

rfidpingtest: __target__/rfidpingtest.js ## compile the rfidpingtest web client (from python to javascript)

__target__/rfidpingtest.js: Makefile rfidpingtest.py  ${LIBS} ${COMMON}
	transcrypt ${OPTS} rfidpingtest

sockwebby: __target__/sockwebby.js ## compile the sockwebby task (from python to javascript)

__target__/sockwebby.js: Makefile sockwebby.py  ${LIBS} ${COMMON}
	transcrypt ${OPTS} -p .none sockwebby

typetest:
	transcrypt ${OPTS} typetest.py
clean: ## remove all javascript code
	rm -f __target__/*

mypy: ##  analyse the webclient code using mypy
	mypy --ignore-missing-imports  webclient.py
force: ## force the compilation of the web client
	rm -f __target__/*.js
	transcrypt ${OPTS} webclient
	transcrypt ${OPTS} rfidpingtest
