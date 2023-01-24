#!/bin/bash

#echo $(pwd)/conda_env/smoother
#source activate $(pwd)/conda_env/smoother

./bin/conf_version.sh

port="$(python3 bin/portscan.py)"

export smoother_port=${port}

cd ..

export smoother_index_path=${1}

export smoother_import_mode="release"
#export smoother_import_mode="debug"
#export smoother_import_mode="redlwdebug"


#gdb python3 -ex "run ~/workspace/smoother/conda_env/smoother/bin/bokeh serve smoother --allow-websocket-origin=localhost:${port} --port ${port}"

bokeh serve smoother --allow-websocket-origin=localhost:${port} --log-level error --port ${port}

# ./run.sh smoother_out/radicl