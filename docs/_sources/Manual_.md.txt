# Smoother Manual

Bulk of the manual

## Table of Contents

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

## Viewing Data

### Example Experiments (_Anna_)

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
| Number of Reads | | Divide the number of interactions in each bin by the total number of reads in the dataset. | ✔️ | ✔️ | ✔️ |
| Column Sum | | Divide the number of interactions in each bin by the number of interactions in the complete column that bin belongs to. | | ✔️ | ✔️ |
| Row Sum | | Divide the number of interactions in each bin by the number of interactions in the complete row that bin belongs to. | | ✔️ | ✔️ |
| Coverage of Normalization Reads (Absolute) | | Divide the number of interactions in each bin by the coverage of the normalization datasets. With the 'Normalization Rows' and 'Normalization Columns' pickers, you can decide what datasets should be used for the columns and rows. | ✔️ | ✔️ | ✔️ |
| Coverage of Normalization Reads (Scaled) | | Same as the absolute version, but makes sure the complete colorscale is used. | ✔️ | ✔️ | |
| Binominal Test | | Use a binominal test to determine weather each bin is statistically significant, in it's row. This strategy was created by Bonetti et al. for RADICL-seq RNA-DNA interaction data [3]. The acceptance p-value can be modified with a slider. \*For views that do not show the entire genome, we use an approximation for the p-value adjustment that is performed after the binominal test. | | ✔️ | ✔️* |
| Iterative Correction | | Use the iterative correction approach developed for Hi-C data by Imakaev et al. [4]. | ✔️ | | ✔️ |

Since smoother is capable of normalizing data on the fly, you can zoom in to a region of interest and then dynamically change the normalization strategy.

Groups A and B are normalized individually and then combined according to the 'Between Group' setting (see Replicates section).
The 'In Group' operation (see Replicates section) is applied before the Normalization.



##### Mapping Quality Bounds

@todo move to Filters

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

<img src="../static/log_scale.png"/>

, where *x* and *y* are the un-normalized and normalized interaction frequencies while *a* is the log base parameter.
With varying values for *a*, this function always satisfies *f(0)=0* and *f(1)=1*.
for *a=0* the function is undefined but approaches the 45-degree diagonal, so we hardcode *f(x)=x* for *a=0*.


#### Quick Config Buttons

what do they change

## Setting up a Webserver (_Markus_)

smoother can be deployed as a webserver so this should be described

## Using Slurm (_Markus_)

smoother can run within slurm 

## Installing via GitHub (_Markus_)

getting the current development version

## The Datastructure (_Markus_)

link to datastructure github

### Brief Algorithmic Description

### Fileformat specification

what files
how are they encoded (link to libSps)

### Implementation Details

some runtime details

## Citing Smoother

## References


[1] Shekelyan, M., Dignös, A. & Gamper, J. Sparse prefix sums: Constant-time range sum queries over sparse multidimensional data cubes. Information Systems 82, 136–147 (2019).

[2] Schmidt et al. @todo

[3] Bonetti, A. et al. RADICL-seq identifies general and cell type–specific principles of genome-wide RNA-chromatin interactions. Nat Commun 11, 1018 (2020).

[4] Imakaev, M. et al. Iterative correction of Hi-C data reveals hallmarks of chromosome organization. Nat Methods 9, 999–1003 (2012).



## Thanks to...
- Bokeh
- Stxxl
- Sparse Prefix Sums paper
- Papers with the normalizations
- Dataset origin