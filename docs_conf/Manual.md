# Smoother Manual

Bulk of the manual

## Table of Contents

## Installing and Running Smoother

### Using Slurm

Smoother is set up to be run on a server within the [Slurm Workload Manager](https://slurm.schedmd.com/overview.html "Go to the Slurm Webpage").
For this, you need to log into the main node of the server with ssh port forwarding.
Port forwarding allows you to reach the smoother application with the webbrowser of your local computer even though it is is running on one of the client nodes on your server.
The default port that needs to be forwarded is 5009; this requires the following login command:

    ssh -L 5009:localhost:5009 -t your_user_name@your_server.com

Now any internet-traffic that is using the port 5009 is directed to the server you just logged in to. 
Then you can navigate into the smoother folder and call the srun.sh script.

    ./srun.sh

This will then log into one of the slurm-client nodes (again using the port forwarding) and start smoother there.
Again the internet-traffic of port 5009 will be redirected, this time from the master node in the server to the client node in the server.
The command will print an url on your terminal.
Follow this url with any webbrowser to open smoother on the server.


### Installing via GitHub

For installing smoother via github, run the following commands:

    # clone repository
    git clone https://github.com/MarkusRainerSchmidt/smoother
    cd smoother

    # create the required conda environment
    ./conda_env/create_smoother_env.sh

    # install using pip
    pip install -e .


### Setting up a Webserver

smoother can be deployed as a webserver so this should be described


## Importing Data

### Preprocessing Data (_Anna_)

generating the chromosome lengths file
annotation file
bed & wig files
input formats
output all alignments
provide some sample files

### Create Index (_Anna_)

creating an empty index
adding genome sizes
and annotation file
min bin size parameter

### Adding Replicates (_Anna_)

adding hi-c or radicl-seq replicates

### Adding Normalization Tracks (_Anna_)

adding read or wig normalization tracks

### Adding Grid-seq normalizations (@todo better name) (_Markus_)

creating relevant plots (infliction point)
setting parameters
adding as normalization track


## List of Features

### List of Plots and what they show (_Anna_)

the heatmap the ratio & coverage plots 
mention hovers
also include status text & command line output


### List of Buttons and their functionality (_Both_)

top to bottom list of things
group by category
don't forget the bokeh buttons

#### Normalization (_Markus_)

##### Normalize by


Smoother can normalize data in various ways. Some of them are suited for symmetric data (e.g. Hi-C), some for asymmetric data (e.g. RADICL-seq).
For some normalizations, views or different regions or with different bin sizes are not comparable.
Note that for these normalizations, even zooming or moving around may skew the displayed values.
It is recommended to use these normalizations merely as an exploratory tool but never to compare e.g. two screenshots of different regions.

| Name | Picture | Description | For Symm. | For Asymm. | Always Comparable |
|-|-|-|-|-|-|
| Largest Rendered Bin | | Divide the number of interactions in each bin the number of interactions in the largest rendered bin. This keeps differences between bins nicely visible by always ensuring that the colorscale is used fully. | ✔️ | ✔️ | |
| Reads per Million | | Divide the number of interactions in each bin by the number of million reads in the dataset. | ✔️ | ✔️ | ✔️ |
| Reads per Thousand | | Divide the number of interactions in each bin by the number of thousand reads in the dataset. | ✔️ | ✔️ | ✔️ |
| Column Sum | | Divide the number of interactions in each bin by the number of interactions in the complete column that bin belongs to. | | ✔️ | ✔️ |
| Row Sum | | Divide the number of interactions in each bin by the number of interactions in the complete row that bin belongs to. | | ✔️ | ✔️ |
| Coverage of Normalization Reads (Absolute) | | Divide the number of interactions in each bin by the coverage of the normalization datasets. With the 'Normalization Rows' and 'Normalization Columns' pickers, you can decide what datasets should be used for the columns and rows. | ✔️ | ✔️ | ✔️ |
| Coverage of Normalization Reads (Scaled) | | Same as the absolute version, but makes sure the complete colorscale is used. | ✔️ | ✔️ | |
| Binominal Test | | Use a binominal test to determine weather each bin is statistically significant, in it's row. This strategy was created by Bonetti et al. for RADICL-seq RNA-DNA interaction data [3]. The acceptance p-value can be modified with a slider. \*For views that do not show the entire genome, we use an approximation for the p-value adjustment that is performed after the binominal test. | | ✔️ | ✔️ \* |
| Iterative Correction | | Use the iterative correction approach developed for Hi-C data by Imakaev et al. [4]. @todo this is ICE correct? | ✔️ | | ✔️ |

Since smoother is capable of normalizing data on the fly, you can zoom in to a region of interest and then dynamically change the normalization strategy.

Groups A and B are normalized individually and then combined according to the 'Between Group' setting (see Replicates section).
The 'In Group' operation (see Replicates section) is applied before the Normalization.

##### Normalizing the RADICL-seq way

@todo

##### Color Scale Begin \& Color Scale Log Base

After normalization, the values in each bin are between zero and one. 
Before displaying these values in the heatmap, we apply a logarithmic transformation.
Like with logarithmic scales, this keeps all values in the same order but this makes a difference between two small numbers appear bigger than the same difference between two bigger numbers.
You can fiddle with the strength of this effect using the 'Color Scale Log Base' slider.
In brief, higher values for the log base increase the difference between small numbers but make larger number look more similar.
Lower values do the opposite.
Setting log base to zero displays the numbers without any transformation.

Additionally, the 'color scale begin' slider can be used to cut off the bottom of the color scale, i.e. to only show bins with more than x interactions. 
This option subtracts from the raw number of interactions; it is applied before normalization and application of the log scale.

In detail, the function we use is:

<img src="./static/log_scale.png"/>

, where *x* and *y* are the un-normalized and normalized interaction frequencies while *a* is the log base parameter.
With varying values for *a*, this function always satisfies *f(0)=0* and *f(1)=1*.
for *a=0* the function is undefined but approaches the 45-degree diagonal, so we hardcode *f(x)=x* for *a=0*.


#### Quick Config Buttons (_Anna_)

what do they change.