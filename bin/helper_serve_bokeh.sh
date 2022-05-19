#!/bin/bash

source activate $(pwd)/conda_env/smoother

port=5009


# setup port forwarding

if [[ ! -f .id_smoother_rsa ]]
then
    ssh-keygen -t rsa -N "" -f .id_smoother_rsa
fi
if ! grep -Fxq "$( cat .id_smoother_rsa.pub )" ~/.ssh/authorized_keys
then
    cat .id_smoother_rsa.pub >> ~/.ssh/authorized_keys
fi

ssh -fNR ${port}:localhost:${port} -i .id_smoother_rsa ${SLURM_JOB_USER}@${SLURM_LAUNCH_NODE_IPADDR}
# serve bokeh
echo "starting bokeh server at: http://localhost:${port}/smoother"
cd ..

#gdb python3 -ex "run /home/mschmidt/.conda/envs/main/bin/bokeh serve smoother/ --allow-websocket-origin=localhost:${port} --port ${port}"

bokeh serve smoother --allow-websocket-origin=localhost:${port} --log-level error --port ${port}


# kill port forwarding process
ps -ef | grep "ssh -fNR ${port}:localhost:${port} -i .id_smoother_rsa ${SLURM_JOB_USER}@${SLURM_LAUNCH_NODE_IPADDR}" | grep -v grep | awk '{print $2}' | xargs kill

