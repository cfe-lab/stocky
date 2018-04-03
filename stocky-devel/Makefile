

BASE_IMAGE_NAME = stocky-base
BASE_DOCKERFILE = stocky-base.dock

# DEVEL_DOCKERFILE = stocky-devel.dock
# DEVEL_IMAGE_NAME = stocky-devel

#NOTE: there may be no leading or trailing spaces on the R.H.S, or the -v option will fail
DEV_SRC           =${HOME}/stocky-devel/stocky
STOCKY_STATE_DIR  =${HOME}/stocky-devel/stocky-devel-state
STOCKY_CONFIG_DIR =${HOME}/stocky-devel/stocky-devel-config


#ENV_OPTS = -ePYTHONPATH=/stockysrc/utils
ENV_OPTS = 

PORTNUM=5000


#NOTE Must run the docker image with --privileged to give the container access to devices
USB_DIR = /dev/bus/usb

DOCKER_RUN_CMD = docker run  --rm --privileged -p=${PORTNUM}:${PORTNUM} \
-v ${STOCKY_STATE_DIR}:/stockystate \
-v ${STOCKY_CONFIG_DIR}:/stockyconfig \
-v ${USB_DIR}:${USB_DIR} -w /stockysrc ${ENV_OPTS} 
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

runlocal:  ## run the stocky docker image interactively with bash.
	${DOCKER_RUN_CMD} -v ${DEV_SRC}:/stockysrc -it ${BASE_IMAGE_NAME} tcsh

runprod: ## run the stocky docker image for production.
	${DOCKER_RUN_CMD} ${BASE_IMAGE_NAME}

clean-logs: ## remove all log files from the stocky-devel-state directory
	rm -f stocky-devel-state/*.log
