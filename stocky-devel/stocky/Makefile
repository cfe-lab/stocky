# Makefile for the stocky directory -- provide some useful functions for development

# NOTE: eit serverlib/tests/conftest.py if you want to add test flags such
# as --with_qai

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
#--
all-test: ## run the unit tests of the server code using pytest
	pytest -v serverlib
single-test:
	pytest -v serverlib -k test_ChemStock
all-coverage: ## run the unit tests of the server code, then show the test coverage 
	coverage run -m py.test serverlib
	coverage report -m --omit="serverlib/tests/*","serverlib/__init__.py"
#--
qai-test: ## run the unit tests that access the test QAI webserver
	# pytest -v serverlib --with_qai --ff --maxfail=1 -k test_qai_helper
	pytest -vvv serverlib --with_qai --ff  -k test_qai_helper
	# pytest -vvv serverlib --with_qai -k test_qai_helper
	#pytest -vvv serverlib --with_qai -k test_reagent_receive
qai-coverage: ## show test coverage of code accessing the test QAI server
	coverage run -m py.test serverlib --with_qai -k test_qai_helper
	coverage report  -m --include="serverlib/qai_helper.py"
#--
chemstock-test: ## run the unit tests that access a local chemstocks YAML file
	pytest -v serverlib --with_chemstock --ff -k test_ChemStock
func-test: ## run the unit tests 
	pytest -v serverlib -k Test_funcs
chemstock-qai-test: ## run the unit tests (chemstock with access to qai)
	pytest -v serverlib --with_cs_qai --ff --maxfail=1 -k test_ChemStock
mypy: ## analyse the server code using mypy
	mypy --ignore-missing-imports  stocky.py serverlib
pep8: ## analyse the server code for compliance with pep8 using codestyle
	pytest --codestyle serverlib
