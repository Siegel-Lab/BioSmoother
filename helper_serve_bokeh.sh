#!/bin/bash

# inform user about whats happening first
echo "opening tunnel to your login node, so that your browser can connect to the bokeh server"
echo "will require password input..."
# setup port forwarding
ssh -fNR 5006:localhost:5006 ${SLURM_JOB_USER}@${SLURM_LAUNCH_NODE_IPADDR}
# serve bokeh
echo "starting bokeh server"
cd ..
bokeh serve heatmap_server/ --allow-websocket-origin=localhost:5006
# kill port forwarding process
ps -ef | grep "ssh -fNR 5006:localhost:5006 ${SLURM_JOB_USER}@${SLURM_LAUNCH_NODE_IPADDR}" | grep -v grep | awk '{print $2}' | xargs kill