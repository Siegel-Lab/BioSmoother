#!/bin/bash

SPHINX_EXECUTABLE=sphinx-build
SPHINX_HTML_DIR=docs
BINARY_BUILD_DIR=docs_conf
SPHINX_CACHE_DIR=_doctrees
SPHINX_TEX_DIR=tex

mkdir -p ${SPHINX_HTML_DIR}
mkdir -p ${SPHINX_CACHE_DIR}

${SPHINX_EXECUTABLE} \
    -E -a -q -b html \
    -d ${SPHINX_CACHE_DIR} \
    ${BINARY_BUILD_DIR} \
    ${SPHINX_HTML_DIR}

# fix missing static files
mkdir -p docs/static/
cp -r docs_conf/static/* docs/static/

mkdir -p docs/biosmoother/static
cp biosmoother/static/favicon.* docs/biosmoother/static

# ${SPHINX_EXECUTABLE} \
#     -E -a -q -b latex \
#     -d ${SPHINX_CACHE_DIR} \
#     ${BINARY_BUILD_DIR} \
#     ${SPHINX_TEX_DIR}

# tectonic tex/*.tex