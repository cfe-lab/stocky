
# OPTS = -dc -ds -n -b -e 6 -s sco_for_TS
# transcript compile options
OPTS = -dc -ds -n -b -e6 --dassert  -s sco_for_TS

# Use this additional option for compiling for nodejs (now 'window' variable)
NODEJSOPT = -p .none
# 

PYTEST_PROG = do_test_all.py
JSTEST_PROG = __javascript__/do_test_all.js


default: help

# NOTE: this code taken from https://gist.github.com/rcmachado/af3db315e31383502660
help: 
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

# default: test01

comp-web: ## compile the test program for the web (load the file test.html into the browser)
	transcrypt ${OPTS} ${PYTEST_PROG}
# node-comp: ## compile the test program for execution in nodejs
#	transcrypt ${OPTS} ${NODEJSOPT} ${PYTEST_PROG}
#
#test-node: ## compile and run the test program in nodejs
#	transcrypt ${OPTS} ${NODEJSOPT} ${PYTEST_PROG}
#	node ${JSTEST_PROG}
test-cpython: ## run the test program in CPython
	python ${PYTEST_PROG}

oldrun:
	phantomjs -debug true  node_modules/es6-shim/es6-shim.js  __javascript__/test_simple.js
run:
	google-chrome --headless --disable-gpu --no-sandbox  file://${JSTEST_PROG}

# node_modules/core-js/es6/symbol.js

