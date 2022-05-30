## Using Slurm (_Markus_)

Smoother is set up to be run on a server within the [Slurm Workload Manager](https://slurm.schedmd.com/overview.html "Go to the Slurm Webpage").
For this, you need to log into the main node of the server, with ssh port forwarding.
The default port that needs to be forwarded is 5009; this requires the following login command:

    ssh -L 5009:localhost:5009 -t your_user_name@your_server.com

Then you can navigate into the smoother folder and call the srun.sh script.

    ./srun.sh

This will then log into one of the slurm-client nodes (again using the port forwarding) and start smoother there.
The command will print an url on your terminal.
Follow this link with any webbrowser to open smoother on the server.

## Installing via GitHub (_Markus_)

For installing smoother via github, run the following commands:

    # clone repository
    git clone https://github.com/MarkusRainerSchmidt/smoother
    cd smoother

    # create the required conda environment
    ./conda_env/create_smoother_env.sh

    # @todo run the install commands -> see bioconda integration


## Setting up a Webserver (_Markus_)

smoother can be deployed as a webserver so this should be described

