#!/bin/bash

SPHINX_EXECUTABLE=sphinx-build
SPHINX_HTML_DIR=docs
BINARY_BUILD_DIR=docs_conf
SPHINX_CACHE_DIR=_doctrees
SPHINX_TEX_DIR=tex
GENERATED_DIR=generated_docs

mkdir -p ${GENERATED_DIR}
python3 docs_conf/split_md.py README.md ${GENERATED_DIR}

mkdir -p ${SPHINX_HTML_DIR}
mkdir -p ${SPHINX_CACHE_DIR}
export SMOOTHER_HIDE_SUBCOMMANDS_MANUAL=true

${SPHINX_EXECUTABLE} \
    -E -a -q -b html \
    -d ${SPHINX_CACHE_DIR} \
    ${BINARY_BUILD_DIR} \
    ${SPHINX_HTML_DIR}

# fix missing static files
mkdir -p ${SPHINX_HTML_DIR}/docs_conf/static/
cp -r docs_conf/static/* ${SPHINX_HTML_DIR}/docs_conf/static/

mkdir -p ${SPHINX_HTML_DIR}/biosmoother/static
cp biosmoother/static/favicon.* ${SPHINX_HTML_DIR}/biosmoother/static

sed -i 's/Index/Contents/' ${SPHINX_HTML_DIR}/genindex.html
sed -i 's/<li class="toctree-l1"><a class="reference internal" href="genindex.html">Index<\/a><\/li>/<li class="toctree-l1"><a class="reference internal" href="genindex.html">Contents<\/a><\/li>/' ${SPHINX_HTML_DIR}/*.html

# ${SPHINX_EXECUTABLE} \
#     -E -a -q -b latex \
#     -d ${SPHINX_CACHE_DIR} \
#     ${BINARY_BUILD_DIR} \
#     ${SPHINX_TEX_DIR}
    
# mkdir -p ${SPHINX_TEX_DIR}/docs_conf/static/
# cp -r docs_conf/static/* ${SPHINX_TEX_DIR}/docs_conf/static/

# mkdir -p ${SPHINX_TEX_DIR}/biosmoother/static
# cp biosmoother/static/favicon.* ${SPHINX_TEX_DIR}/biosmoother/static

# tectonic tex/*.tex