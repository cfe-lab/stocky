
# Makefile to facilitate the building and running of Stocky.
# ****** Simply run 'make' in this directory to get a list of options *******

# this is the docker image that we use for development and production
BASE_IMAGE_NAME = stocky-base
BASE_DOCKERFILE = ${BASE_IMAGE_NAME}.dock

# in addition, we have another one that adds additional software needed
# to produce documentation.
DOCS_IMAGE_NAME = stocky-docs
DOCS_DOCKERFILE = ${DOCS_IMAGE_NAME}.dock


STOCKY_TOP_DIR = ${CURDIR}

# NOTE: there may be no leading or trailing spaces on the R.H.S of the equals sign of these
# variables, otherwise the docker -v option will fail when launching
# NOTE: In addition, docker requires an absolute path name for these directories
DEV_SRC           =${STOCKY_TOP_DIR}/stocky
STOCKY_STATE_DIR  =${STOCKY_TOP_DIR}/../stocky-state
STOCKY_CONFIG_DIR =${STOCKY_TOP_DIR}/../stocky-config

# the name of the docker container (NOT image) used for production
STOCKY_PROD_NAME=stockyprod

#ENV_OPTS = -ePYTHONPATH=/stockysrc/utils
ENV_OPTS = 

# the stocky server will listen on this port
PORTNUM=5000

#NOTE Must run the docker image with --privileged to give the container access to devices
DEV_DIR = /dev

DOCKER_TESTRUN_CMD = docker run  --rm --privileged -p=${PORTNUM}:${PORTNUM} \
-v ${STOCKY_STATE_DIR}:/stockystate \
-v ${STOCKY_CONFIG_DIR}:/stockyconfig \
-w /stockysrc ${ENV_OPTS} 

# -p=${PORTNUM}:${PORTNUM} 
DOCKER_RUN_CMD = docker run  --rm --privileged --net=host \
-v ${STOCKY_STATE_DIR}:/stockystate \
-v ${STOCKY_CONFIG_DIR}:/stockyconfig \
-v ${DEV_DIR}:${DEV_DIR} -w /stockysrc ${ENV_OPTS} 


default: help

# NOTE: this code taken from https://gist.github.com/rcmachado/af3db315e31383502660
help: ## This Makefile can be used to build and run the stocky docker images.
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


build: $(BASE_DOCKERFILE) ## build the docker image for stocky
	( docker build  -f $(BASE_DOCKERFILE) -t ${BASE_IMAGE_NAME} . )

build-nocache: $(BASE_DOCKERFILE) ## build the docker image for stocky from scratch
	( docker build --no-cache -f $(BASE_DOCKERFILE) -t ${BASE_IMAGE_NAME} . )

runlocal:  ## run the stocky docker image with local code interactively with bash.
	${DOCKER_RUN_CMD} -v ${DEV_SRC}:/stockysrc -it ${BASE_IMAGE_NAME} tcsh

runprod: ## run the stocky docker image for production.
	${DOCKER_RUN_CMD} -d --name ${STOCKY_PROD_NAME} ${BASE_IMAGE_NAME}
	notify-send "stocky server is running"
stopprod: ## stop a container previously srated with runprod
	docker stop ${STOCKY_PROD_NAME}
	notify-send "stocky server stopped"
runtests:  ## run the unit tests on the stocky docker image with image code 
	${DOCKER_TESTRUN_CMD}  -it ${BASE_IMAGE_NAME} make all-test pep8

build-docs: $(BASE_DOCKERFILE) ## build the stocky-docs docker image for stocky
	( docker build  -f $(DOCS_DOCKERFILE) -t ${DOCS_IMAGE_NAME} . )
run-docs:  ## run the stocky-docs docker image with local code interactively with tcsh
	${DOCKER_RUN_CMD} -v ${DEV_SRC}:/stockysrc -it ${DOCS_IMAGE_NAME} tcsh

clean-logs: ## remove all log files from the stocky-devel-state directory
	rm -f stocky-devel-state/*.log
