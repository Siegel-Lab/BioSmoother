#!/bin/bash

source activate $(pwd)/conda_env/smoother

./bin/conf_version.sh

port="$(python3 bin/portscan.py)"

export smoother_port=${port}

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
cd ..

#gdb python3 -ex "run /home/mschmidt/workspace/anna/smoother/conda_env/smoother/bin/bokeh serve smoother/ --allow-websocket-origin=localhost:${port} --port ${port}"

bokeh serve smoother --allow-websocket-origin=localhost:${port} --log-level error --port ${port}


# kill port forwarding process
ps -ef | grep "ssh -fNR ${port}:localhost:${port} -i .id_smoother_rsa ${SLURM_JOB_USER}@${SLURM_LAUNCH_NODE_IPADDR}" | grep -v grep | awk '{print $2}' | xargs kill

