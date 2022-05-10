#!/bin/bash

source activate smoother_docs


SPHINX_EXECUTABLE=sphinx-build
SPHINX_HTML_DIR=docs
BINARY_BUILD_DIR=docs_conf
SPHINX_CACHE_DIR=_doctrees
SPHINX_TEX_DIR=tex

mkdir ${SPHINX_HTML_DIR}
mkdir ${SPHINX_CACHE_DIR}

${SPHINX_EXECUTABLE} \
    -E -a -q -b html \
    -d ${SPHINX_CACHE_DIR} \
    ${BINARY_BUILD_DIR} \
    ${SPHINX_HTML_DIR}

# fix missing static files
cp -r static docs/static

${SPHINX_EXECUTABLE} \
    -E -a -q -b latex \
    -d ${SPHINX_CACHE_DIR} \
    ${BINARY_BUILD_DIR} \
    ${SPHINX_TEX_DIR}

tectonic tex/*.tex