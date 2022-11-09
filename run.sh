#!/bin/bash

#echo $(pwd)/conda_env/smoother
#source activate $(pwd)/conda_env/smoother

./bin/conf_version.sh

port="$(python3 bin/portscan.py)"

export smoother_port=${port}

cd ..

gdb python3 -ex "run ~/workspace/smoother/conda_env/smoother/bin/bokeh serve smoother --allow-websocket-origin=localhost:${port} --log-level error --port ${port}"

#bokeh serve smoother --allow-websocket-origin=localhost:${port} --log-level error --port ${port} 