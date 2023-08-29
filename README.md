<img src="https://raw.githubusercontent.com/Siegel-Lab/BioSmoother/master/biosmoother/static/favicon.png" align="center" width="90">

Smoother is still under development. More information will be added soon.

## Quick Start

create & activate a new environment (optional)
```
conda create -y -n smoother python=3.9
conda activate smoother
```

Install smoother (and all requirements) using pip.
```
pip install biosmoother
conda install -y nodejs # pip cannot install nodejs, so we use conda
```

Download 2 example smoother indices.
```
wget https://syncandshare.lrz.de/dl/fiFPBw32Rc3cJs1qfsYkKa/radicl.smoother_index.zip
wget https://syncandshare.lrz.de/dl/fi8q6iroKx49azsZLHxeYB/micro-c.smoother_index.zip

conda install unzip
unzip radicl.smoother_index.zip
unzip micro-c.smoother_index.zip
```

View one of the indices
```
biosmoother serve micro-c --show
#biosmoother serve radicl --show
```
