#!/bin/bash

port=5006

# inform user about whats happening first
echo "opening tunnel to your login node, so that your browser can connect to the bokeh server"
echo "will require password input..."
# setup port forwarding
ssh -fNR ${port}:localhost:${port} ${SLURM_JOB_USER}@${SLURM_LAUNCH_NODE_IPADDR}
# serve bokeh
echo "starting bokeh server at: http://localhost:${port}/smoother"
cd ..

#gdb python3 -ex "run /home/mschmidt/.conda/envs/main/bin/bokeh serve smoother/ --allow-websocket-origin=localhost:${port} --port ${port}"
bokeh serve smoother/ --allow-websocket-origin=localhost:${port} --log-level error --port ${port}

# kill port forwarding process
ps -ef | grep "ssh -fNR ${port}:localhost:${port} ${SLURM_JOB_USER}@${SLURM_LAUNCH_NODE_IPADDR}" | grep -v grep | awk '{print $2}' | xargs kill