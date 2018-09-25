#!/bin/bash

# run some really basic tests to make sure our plantuml installation
# is working.

#NOTE: these tests are to be run from within a docker image, in which the
# plantuml.jar has been installed in /plantuml/...

# test graphviz dependency
java -jar /plantuml/plantuml.jar -testdot

# produces seqtest.png
echo "producing seqtest.png..."
java -jar /plantuml/plantuml.jar seqtest.uml

# produces seqtest.svg
echo "producing seqtest.svg..."
java -jar /plantuml/plantuml.jar -tsvg seqtest.uml


