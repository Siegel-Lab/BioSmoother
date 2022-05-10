#!/bin/bash

source activate smoother
source activate smoother_docs


SPHINX_EXECUTABLE=sphinx-build
SPHINX_HTML_DIR=docs
BINARY_BUILD_DIR=_docs_build
SPHINX_CACHE_DIR=_doctrees

mkdir ${SPHINX_HTML_DIR}

${SPHINX_EXECUTABLE} \
    -E -a -q -b html \
    -d ${SPHINX_CACHE_DIR} \
    ${BINARY_BUILD_DIR} \
    ${SPHINX_HTML_DIR}