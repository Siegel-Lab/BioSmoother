#!/bin/bash

#echo $(pwd)/conda_env/smoother
#source activate $(pwd)/conda_env/smoother

./bin/conf_version.sh
port=5009

echo "starting bokeh server at: http://localhost:${port}/smoother"
cd ..
bokeh serve smoother --allow-websocket-origin=localhost:${port} --log-level error --port ${port} 