#!/bin/bash

#echo $(pwd)/conda_env/smoother
#source activate $(pwd)/conda_env/smoother

./bin/conf_version.sh

port="$(python3 bin/portscan.py)"

export smoother_port=${port}

cd ..

export smoother_index_path=${1}


# export PYTHONPATH="$(pwd)/libSmoother/build_rel_w_dbg/":$PYTHONPATH
# export PYTHONPATH="$(pwd)/libSmoother/build_dbg/":$PYTHONPATH
# gdb python3 -ex "run ~/workspace/smoother/conda_env/smoother/bin/bokeh serve smoother --allow-websocket-origin=localhost:${port} --port ${port}"

#export PYTHONPATH="$(pwd)/libSmoother/build_rel/":$PYTHONPATH
bokeh serve smoother --allow-websocket-origin=localhost:${port} --log-level error --port ${port}

# ./run.sh smoother_out/radicl