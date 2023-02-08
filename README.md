<img src="https://raw.githubusercontent.com/Siegel-Lab/Smoother/master/smoother/static/favicon.png" align="center" width="90">

# Smoother

@todo

## Abstract-like hook

## Quick Start

create & activate a new environment (optional)
```
conda create -y -n smoother python=3.8
conda activate smoother
```

Install conda-specific requirements
```
# make sure the proper compiler is installed
conda install -y gcc=9.4.0 gxx=9.4.0 -c conda-forge
# install requirements of smoother serve
conda install -y nodejs tornado
```

Install smoother (and all requirements) from GitHub.
```
pip install git+https://github.com/Siegel-Lab/Smoother.git --no-binary libsps,libsmoother
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
smoother serve micro-c --show
#smoother serve radicl --show
```

## Web-version


## Usage


## Quick config Buttons

## Manual

## Citing Smoother

## References

