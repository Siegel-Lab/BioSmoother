#!/bin/bash

port=5007

# inform user about whats happening first
echo "opening tunnel to your login node, so that your browser can connect to the bokeh server"
echo "will require password input..."
# setup port forwarding
ssh -fNR ${port}:localhost:${port} ${SLURM_JOB_USER}@${SLURM_LAUNCH_NODE_IPADDR}
# serve bokeh
echo "starting bokeh server at: http://localhost:${port}/smother"
cd ..
export SPATIALINDEX_C_LIBRARY="$(pwd)/heatmap_server/libspatialindex_c.so"

#gdb python3 -ex "run /home/mschmidt/.conda/envs/main/bin/bokeh serve heatmap_server/ --allow-websocket-origin=localhost:${port} --port ${port}"
bokeh serve smother/ --allow-websocket-origin=localhost:${port} --log-level error --port ${port}

# kill port forwarding process
ps -ef | grep "ssh -fNR ${port}:localhost:${port} ${SLURM_JOB_USER}@${SLURM_LAUNCH_NODE_IPADDR}" | grep -v grep | awk '{print $2}' | xargs kill