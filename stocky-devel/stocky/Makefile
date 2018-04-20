# Makefile for the stocky directory -- provide some useful functions for development


default: help

# NOTE: this code taken from https://gist.github.com/rcmachado/af3db315e31383502660
help: ## Test the stocky server code
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

web: ## compile the webclient
	$(MAKE) -C webclient webclient to javascript
test-all: ## run all unit tests of the server code using pytest
	pytest
mypy: ## analyse the server code using mypy
	mypy --ignore-missing-imports  stocky.py
test-coverage: ## Show the test coverage of the server code
	pytest --cov
