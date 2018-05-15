# Makefile for the stocky directory -- provide some useful functions for development


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

web: ## compile the webclient using transcrypt
	$(MAKE) -C webclient webclient
test-all: ## run the unit tests of the server code using pytest
	pytest serverlib
mypy: ## analyse the server code using mypy
	mypy --ignore-missing-imports  stocky.py serverlib
test-coverage: ## run the unit tests of the server code, then show the test coverage 
	coverage run -m py.test serverlib
	coverage report --omit="serverlib/tests/*","serverlib/__init__.py"
pep8: ## analyse the server code for compliance with pep8 using codestyle
	pytest --codestyle serverlib
