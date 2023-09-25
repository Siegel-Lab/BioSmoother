<p align="center">
    <img src="./biosmoother/static/favicon.png" width="180">
</p>

Smoother is an interactive analysis and visualization software for contact mapping data. 

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
wget @todo
#wget @todo

conda install unzip
unzip radicl.smoother_index.zip
#unzip micro-c.smoother_index.zip
```

View one of the indices
```
biosmoother serve micro-c --show
#biosmoother serve radicl --show
```

## Manual

A full manual can be found here @todo.

## Overview

In Smoother, parameters can be changed on-the-fly.
This means, a user can click a button or move a slider and will immediately see the effect of that parameter change on screen.
Parameters that can be changed include:

<img src="./docs_conf/static/all_features.gif">

## Loading your own data

All data needs to be converted into a smoother index first.
For this, first create an empty index:
```
biosmoother init my_index my_genome.sizes my_annotation.gff
```
Here, `my_genome.sizes` is a file that contains the length of each chromosome in your genome and `my_annotation.gff` contains the genomes annotations.

Then, add your data to the index:
```
biosmoother repl my_index my_replicate_1.tsv name_of_replicate_1
biosmoother repl my_index my_replicate_2.tsv name_of_replicate_2
...
```
Here `my_replicate_x.tsv` needs to be a tab-separated file with 10 columns: `read_id, chr1, pos1, chr2, pos2, strand1, strand2, pair_type, mapq1, and mapq2`.

Finally, the index can be opened with:
```
biosmoother serve my_index --show
```

## Cite

If you use smoother in your research, please cite:
@todo
