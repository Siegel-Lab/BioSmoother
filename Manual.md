# Manual
## Summary
Smoother is an interactive analysis and visualisation software for nucleic acid interactome data that allows the change of parameters such as normalisation, bin size or MAPQ on the fly. Smoother can load multiple samples which can be grouped and compared. Smoother also allows filtering by annotations and the display of coverage for additional sequencing data. 
(Smoother's index)
Smoother is centred on an index including the genome, annotations and datasets to be analysed and visualised.
(Paradigm shift)
-	On-the-fly processing is made possible through this index for the first time
## Installation
The easiest way to install Smoother is via pip

    pip install biosmoother

This will install the `biosmoother`, the graphical user interface and `libbiosmoother` the backend behind the GUI and the command-line interface.
### Compiling yourself
For installing smoother via GitHub, run the following commands:

    # clone repository
    git clone https://github.com/Siegel-Lab/BioSmoother.git

    # create the required conda environment
    ./conda_env/create_smoother_env.sh

    # install using pip
    pip install -e .

While the pip installation will install the latest stable release, this type of installation will install the newest, possibly untested version. Note that this approach does still use pip to install the latest stable release of libBioSmoother and libSps, the two backend libraries behind smoother. To also install these two libraries on your own, you will have to clone the respective repositories and install manually from them using the `pip install -e .` command. Then you can install smoother using `pip install -e . –no-deps` to install smoother without adjustments to the dependencies.
## Usage
### Command organization into main and subcommands
Smoother has multiple sub-commands, all of which interact with an index directory. An index contains the genome, its annotations, as well as the datasets to be analysed and visualised. Each of the subcommands is designed to perform one specific task on the index. For example, there are the `init` and `serve` subcommands that can be called as follows:

	biosmoother init …
	biosmoother serve …

A complete list of subcommands can be found [here](https://biosmoother.readthedocs.io/en/latest/Cli.html). The following chapters explain how to use the subcommands to create new indices and interact with them.
### Creating an index
All data to be analysed and visualized on Smoother needs to be precomputed into an index. In the next chapters we will explain how to create an index and fill it with data.
#### Initializing an index
Before an index can be filled with interactome data, we have to set it up for a given a reference genome and with a given maximum resolution which corresponds to the minimal bin size that can be displayed and analysed. Generating an empty index is done using the `init` sub-command. The command outputs an index directory.

Let us create a new index for a trypanosome genome.

	biosmoother init my_index tryp.sizes

This command will create a folder called `my_index.smoother_index`. In all other subcommands, we can now use `my_index` to refer to this index. `tryp.sizes` is a file that contains the contig sizes of out Trypanosome genome. It looks something like this:

	#contig_name contig_size
	chr1 123438
	chr2 46546

If we have a .gff file, containing annotations for our genome, we must include this file right when creating the index:

	biosmoother init my_index tryp.sizes tryp_anno.gff

This gff file must match the [GFF specifications](http://gmod.org/wiki/GFF3), and looks something like this:

	Example gff data
	Example gff data

> Tipp: Indices might become very large (multiple hundreds of gigabytes). The easiest way to reduce index size is to increase the base resolution of the index. For this, you can use the `-d` parameter of the `init` subcommand. The base resolution is the highest resolution that can be displayed, so do not set it lower than the resolutions you are interested in.
The full documentation of the `init` sub-command can be found here http://gmod.org/wiki/GFF3.
#### Adding replicates to an index
Adding data for a sample or replicate to an index is done with the `repl` sub-command. This requires an input pairs file containing the two-dimensional interactome matrix for the aligned reads. Pre-processing of the data and input pairs file generation are explained in detail in the next section (3. Data pre-processing and input generation).

The basic usage of the `repl` subcommand is as follows:

	biosmoother repl my_index replicate_data.tsv replicate_name

Here, `my_index` is the index the data shall be added to, `replicate_data.tsv` is a file containing the actual data, and `replicate_name` is the displayname of that dataset in the user interface.
There is a way to load gzipped (or similar) datafiles into smoother using pipes:

	zcat replicate_data.tsv.gz | biosmoother repl my_index – replicate_name 

The full documentation of the `repl` sub-command can be found [here](https://biosmoother.readthedocs.io/en/latest/Cli.html#repl).
##### Proper input format
Smoother requires a whitespace (space or tab) delimited input pairs file containing the two-dimensional interactome matrix for the aligned reads. This input pairs file contains the data for each sample or replicate to be analysed and visualised. Each row has the information for one read. Each sample or replicate requires an individual input pairs file.

The default format for the input pairs file is compatible with the output from pairtools and corresponds to the following -C option for the repl sub-command: -C [readID] chr1 pos1 chr2 pos2 [strand1] [strand2] [.] [mapq1] [mapq2] [xa1] [xa2] [cnt].

Smoother supports input files formatted as count matrices, corresponding to the -C option ['chr1', 'pos1', 'chr2', 'pos2', 'cnt']. However, the limited information in such files won`t allow Smoother to perform analyses at its full potential. It is important to notice that count matrices are already binned and thus the 'pos' columns correspond to the bin position. Thus, setting a smaller bin size with the -d option in the init sub-command or running analyses with the annotation filtering will not provide useful information and should be avoided.

See the table below for a summary of filtering functionalities of Smoother depending on the input pairs file format with which the index has been generated:

<img src="./docs_conf/static/filtering_functions.png">

A: column must exist

X: column cannot exist

Y: column exists 

N: column does not exist

On: filter is active

Off: filter is inactive

Off*: filter can be active, but it is uninformative because position is binned



In the following sub-sections, we describe examples of the pre-processing workflow from raw demultiplexed fastq files to input pairs files for symmetric and asymmetric data sets.
##### Preprocessing data
###### Symmetric data sets, such as Hi-C or Micro-C
The following steps are one example that can be followed to produce the input pairs files necessary to generate the index for Smoother from raw Hi-C data.
(ABS: is there no need of step inputting the restriction enzyme(s) used to understand what are valid pairs, right? I see pairtools also have a restrict command…)

The raw read files are mapped to the reference genome using bwa mem.

    bwa mem -t 8 -SP ${GENOME_NAME}.fna ${READ_FILE_1} ${READ_FILE_2}

Find ligation junctions and make pairs file using pairtools parse (ref? but then also for bwa and everything?) with the following options:
	--drop-sam: drop the sam information
	--min-mapq 0: do not filter by mapping quality
	--add-columns mapq,XA: add columns for mapping quality and alternative alignments
	--walks-policy mask: mask the walks (WW, XX, N*) in the pair_type column

    pairtools parse --drop-sam --min-mapq 0 --add-columns mapq,XA --walks-policy mask ${GENOME_NAME}.sizes

Filter out the walks (WW, XX, N*) from the pairs file using pairtools select

    pairtools select '(pair_type!="WW") and (pair_type!="XX") and not wildcard_match(pair_type, "N*")' {OUTPUT_PARSE}.pairs

Sort the output using pairtools sort

    pairtools sort --nproc 8 {OUTPUT_SELECT}.pairs

Deduplicate the output using pairtools dedup

    pairtools dedup {OUTPUT_SORT}.pairs

Generate the final pairs file that will be the input for generating Smoother index using pairtools split

    pairtools split {OUTPUT_DEDUP}.pairs --output-pairs ${SAMPLE_NAME}.pairs.gz

Below an example of some lines of a Hi-C input pairs file that can be used to generate the Smoother index.

Here paste first lines of one input Hi-C pairs file, formatted as text file.


###### Asymmetric data sets, such as RD-SPRITE, or RADICL-seq
The following steps are one example that can be followed to produce the input pairs files necessary to generate the index for Smoother from single-read raw RADICL-seq (ref) data.

First round of extraction of the RNA and DNA tags from the chimeric reads containing the RADICL adapter sequence using tagdust. Here read1 will be RNA and read2 will be DNA.

    tagdust -1 R:N -2 S:CTGCTGCTCCTTCCCTTTCCCCTTTTGGTCCGACGGTCCAAGTCAGCAGT -3 R:N -4 P:AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC {READ_FILE} -t 38 -o {out1_R1D2}

Second round of extraction of the RNA and DNA tags from the chimeric reads containing the RADICL adapter sequence using tagdust. Here read1 will be DNA and read2 will be RNA.

    tagdust -1 R:N -2 S:ACTGCTGACTTGGACCGTCGGACCAAAAGGGGAAAGGGAAGGAGCAGCAG -3 R:N -4 P:AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC {out1_R1D2} -t 38 -o {out2_D1R2}

Concatenate two files with RNA reads using fastx_toolkit.

    cat {out1_R1D2_READ1}.fq > {RNA}.fq
    cat {out2_D1R2_READ2}.fq | fastx_reverse_complement -Q33 >> {RNA}.fq

Concatenate two files with DNA reads using fastx_toolkit.

    cat {out1_R1D2_READ2}.fq | fastx_reverse_complement -Q33 >> {DNA}.fq
    cat {out2_D1R2_READ1}.fq > {DNA}.fq

The RNA and DNA read files are mapped to the reference genome using bwa aln with -N parameter to keep the multimapping reads.

    bwa aln -N ${GENOME_NAME}.fna {RNA}.fq > {RNA}.sai
    bwa aln -N ${GENOME_NAME}.fna {DNA}.fq > {DNA}.sai

Convert the output from the alignment to SAM format with a value for the -n parameter high enough to keep all interesting multimapping reads.
 
    bwa samse -n 60 ${GENOME_NAME}.fna {RNA}.sai {RNA}.fq > {RNA}.sam
    bwa samse -n 60 ${GENOME_NAME}.fna {DNA}.sai {DNA}.fq > {DNA}.sam
 
Generate tab-separated text files for RNA and for DNA with the information from the SAM files and adding dummy values (notag) if there is no XA tag.

    cat {RNA}.sam | awk -F '\t' 'BEGIN {OFS="\t";ORS=""} {if ($1 ~ !/^@/ && $3 ~ !/*/) {print $3,$4,$1,$5; for(i=12;i<=NF;i+=1) if ($i ~ /^XA:Z:/) print "",$i; print "\n"}}' | awk -F '\t' 'BEGIN {OFS="\t";ORS=""} {print $1,$2,$3,$4; if(NF<5) 
print "\tnotag"; else print "",$5; print "\n"}' >> {RNA}

    cat {DNA}.sam | awk -F '\t' 'BEGIN {OFS="\t";ORS=""} {if ($1 ~ !/^@/ && $3 ~ !/*/) {print $3,$4,$1,$5; for(i=12;i<=NF;i+=1) if ($i ~ /^XA:Z:/) print "",$i; print "\n"}}' | awk -F '\t' 'BEGIN {OFS="\t";ORS=""} {print $1,$2,$3,$4; if(NF<5) 
    print "\tnotag"; else print "",$5; print "\n"}' >> {DNA}
 
Sort the RNA and DNA tab-separated text files.

    sort -k1,1 -k2,2n {RNA} > {RNA_k1k2}
    sort -k1,1 -k2,2n {DNA} > {DNA_k1k2}
    sort -k3,3 {RNA_k1k2} > {RNA_k3}
    sort -k3,3 {DNA_k1k2} > {DNA_k3}

Merge the RNA and DNA files based on the sequencing ID (column 3) to generate a single interactome file.

    join -j 3 {RNA_k3} {DNA_k3} | awk 'BEGIN{OFS="\t"}{print $2,$3,$1,$4,$5,$6,$7,$1,$8,$9}' > {R_D}

Sort the merged interactome file {R_D} by genomic location of the RNA interaction partner. (ABS: I think this and the next steps are in fact no needed? And I guess everything could anyway be easily piped.This was how I was doing in old way but never tried with new flexible input format, shoul I modify for that or we just cut down all the sortings?)

 
 Below an example of some lines of a RADICL-seq input pairs file that can be used to generate the Smoother index.

 
Here paste first lines of one input RADICL pairs file, formatted as text file.

#### Adding tracks to an index
Adding uni-dimensional data to an index is done with the `track` sub-command. Pre-processing of the data and input file generation are explained in detail in the next section (3. todo).

The basic usage of the `track` subcommand is as follows:

	biosmoother track my_index track_data.tsv track_name

Here, `my_index` is the index the data shall be added to, `track_data.tsv` is a file containing the actual data, and `track_name` is the displayname of that dataset in the user interface.
There is a way to load gzipped (or similar) datafiles into smoother using pipes:

	zcat track_data.tsv.gz | biosmoother repl my_index – track_name 

The full documentation of the `track` sub-command can be found here.
##### Proper input format
todo
##### Preprocessing data
Todo
#### Correcting an index for aneuploidy
Many genomes are aneuploid or comprise high levels of heterozygosity in their chromosomes to the extent that correction for practical ploidy is required in order to not over- or under-represent reads coming from these regions (ABS: I think you should not say that chromosomes have different ploidies as that is not really correct, and interactions are not only distributed in polyploid because diploid does not count as polyploid that is only from 3 chromosome sets). Smoother can correct for these genomic imbalances by distributing interactions among varying-ploidy contig sets (see section 4.3.2. Normalise) and this ploidy correction can also be run independently of launching Smoother with the ploidy sub-command.
### Using the graphical user interface
#### Launching the graphical user interface
Launching the Smoother interface for an existing index is done with the `serve` sub-command. If an index has already been launched before, the session will be restored with the parameters of the last session, as they are saved in the session.json file in the index directory. The Smoother interface makes use of the [Bokeh library](http://bokeh.org). For example, this is how we would launch an index called `my_index`:

	biosmoother serve my_index –show

The full documentation of the `serve` sub-command can be found [here](https://biosmoother.readthedocs.io/en/latest/Cli.html#serve).

##### Port forwarding on a server that uses slurm

Smoother requires forwarding from the local computer to the master node. Example for a HPC cluster:

    ssh -L 5006:localhost:5006 -t name@address.com "cd /work_directory ; bash"

If using a cluster system with slurm, the port might need being forwarded from the client to the master node:

    if [[ ! -f .id_smoother_rsa ]]
    then
        ssh-keygen -t rsa -N "" -f .id_smoother_rsa
    fi
    if ! grep -Fxq "$( cat .id_smoother_rsa.pub )" ~/.ssh/authorized_keys
    then
        cat .id_smoother_rsa.pub >> ~/.ssh/authorized_keys
    fi
    ssh -fNR 5006:localhost:5006 -i .id_smoother_rsa ${SLURM_JOB_USER}@${SLURM_LAUNCH_NODE_IPADDR}


##### Setting up a webserver with smoother

@todo

##### Resetting an index
To reset to the default parameters for a given index, Smoother implements the `reset` sub-command. Using reset will erase the saved parameters from the previous session for that index. Example:
	
	biosmoother reset my_index

The full documentation of the `reset` sub-command can be found [here](https://biosmoother.readthedocs.io/en/latest/Cli.html#reset).
#### Navigation on smoother
Navigation on Smoother is controlled by the panels on the top. On the top left, the two arrows allow undoing and redoing changes. (ABS:do they? Haha) On the top central panel, the coordinates for the visible region are displayed and can be modified to navigate to a region of interest, as described in the navigation bar chapter below. On the top right, several tools to interact with the plots can be activated (see the plot tools chapter below).

##### Plot tools
The control panel on the top right corner has the following buttons from left to right: *pan, box zoom, wheel zoom, information, crosshair* and *reset*.

<img src="./docs_conf/static/navigation.png" width=50%>

- *Pan* enables navigation by clicking and moving the heatmap.
- *Box zoom* allows to zoom into a region of interest by selecting the region with a box.
- *Wheel zoom* enables zooming in and out by scrolling. 
- *Hover* displays information for the genomic coordinates, interaction score, and reads by group for the current bin of the heatmap. *Hover* also displays information of the name and colour of displayed coverage tracks and the scores for the current bins in the coverage track.
- *Crosshair* highlights the row and column coordinates of the current location.
- *Reset* resets the heatmap to default settings.

<img src="./docs_conf/static/hover.png" width=50%>

##### The navigation bar
The navigation bar on the top centre of the graphical interface displays the currently visible region, every time smoother renders a new heatmap. However, you can also input a location into the bar and smoother will jump to that location in the heatmap.

For this, click into the bar and replace the text with the region you want to jump to. (A simple way to replace all text in the bar is clicking into it and hitting control-a, then typing the new location).

The bar accepts the following syntax and various short forms of if:
	
	X=[chrX1: 10 kbp .. chrX2: 100 kbp] Y=[chrY1: 20 kbp .. chrY2: 200 kbp]

Here, `chrX1: 10 kbp` is the start horizontal location, while `chrX2: 100 kbp` is the horizontal end location. The same goes for `chrY1` and `chrY2` as the vertical start and end locations. Several units are accepted: `bp`, `kbp`, and `Mbp`. The square brackets around the coordinates of either axis are optional. Note that two dots `..` are used to delimitate the start and end locations on an axis; this is essential, you cannot use one, three or more dots.

If you want to merely change the range of the x-axis, you can omit the `Y=[…]` portion of the command (vice versa for the y-axis).
	
	X=[chrX1: 10 kbp .. chrX2: 100 kbp]

If you want to change both axis to the same region, simply drop the `X=` and `Y=`

	chr1: 10 kbp .. chr2: 100 kbp

If the entire contig shall be visible, coordinates can be omitted:
	
	chr1 .. chr2

Here the heatmap would include `chr1` and `chr2` fully: I.e., start at the beginning of `chr1` and end at the ending of `chr2`. If `chr1` equals `chr2`, this can be expressed even simpler:

	chr1

Let's say you want to display `chr1`, with `100 kbp` of extra space around it, you could use the following command:
	
    chr1: +- 100 kbp

Instead of adding extra space around the entire contig, one can also pick a specific position. For example, one could show the region from 400 kbp to 600 kbp on chr1.

	chr1: 500 kbp +- 100 kbp

Further, showing the region from `100 kb` to `200 kbp` on `chr1` is also possible:

	chr1: 100 kbp .. 200 kbp

Negative coordinates are allowed, the following command will show a 200 kbp region centred around the start of chr1:

	chr1: -100 kbp .. 100 kbp

Capitalization does not matter for all inputs to the navigation bar. 

> Tip: Inputting a '`*`' into the navigation bar will make the full heatmap visible.

#### Settings tabs
On the right-hand side of the interface, there are several tabs with buttons and sliders. These can be used to change several analysis parameters on-the-fly.
##### File

In the *File* tab of Smoother, there are three sub-tabs: *Presetting, Export* and *Info*.

*Presetting* allows performing analysis with predetermined settings. Three analyses are already preconfigured and available on Smoother for doing normalisations as in GRID-seq (ref), RADICL-seq (ref), and for mirroring data and performing iterative correction (ref) for Hi-C data. It is also possible to save the current settings configured on Smoother as a new pre-set analysis, this will save all configuration but not the zoomed area of the session.

*Export* allows to save the interactome data with the settings of the current session either as a TSV text file with the interactions or as a picture in SVG or PNG format. It is possible to export the visible region or mark the option to export the full matrix instead.
-	The path for the exported files can be specified on the *Output Prefix* box.
-	The format can be selected clicking on the *Format* arrow.
-	If files need to be exported to the server instead of downloading them it is possible to tick the box *Export files to server instead of downloading them*
-	The pixel size for coordinates, contigs, secondary axis and stroke width can be selected prior to export.
-	When saving as TSV, 3 files are saved, one for the interactome, and one for each axis.
Exporting with settings thus allows to save interactome data with all active filters, normalisation, comparison between groups, and even virtual 4C analyses. 

*Info* provides a log of Smoother processes, which are also displayed on the command line.
-	*Download current session* allows exporting the metadata by downloading all the parameters of the current session.

##### Normalise
In the *Normalise* tab of Smoother, there are three sub-tabs: *Main, Dist. Dep. Dec.* and *Ploidy*.

Several normalisations are available in the *Main* sub-tab to normalise the heatmap or the coverage track. The heatmap and coverage can be normalised by *Reads per million* or *Reads per thousand* on the visible region. It is worth noting that the visible colour changes automatically on screen (can be modified on the View tab) and thus the heatmap might not change visually between *No normalisation, Reads per million or Reads per thousand*, despite the values of the bins do change which are what is relevant for exporting the TSV text file for downstream analyses. The coverage can also be normalised by *Reads per million base pairs* and *Reads per thousand base pairs*, so that normalisation can be done by count of current bin over the size of the bin, indicating the density of reads in one million or thousand base pair squared.

The other normalisations available for heatmap on Smoother are performed with a sampling strategy that also considers some bins outside of the visible area for normalisation (ref Smoother paper needed or not). The normalisations available for the heatmap based on the sampling strategy are *Binomial test* (ref RADICLseq), *Iterative correction* (ref) and *Associated slices* (ref GRID-seq). The number of samples taken outside the visible region can be modified on the slider bar *Number of samples* to ensure the lowest deviation from normalising to the entire heatmap (ref Smoother paper needed or not, but that is only for our genome…). If it is essential that the normalisation runs on the entire heatmap it is possible to export the interactome and generate a new index on Smoother with the normalised data that allows zooming in to regions normalised to the entire heatmap. The *Binomial test* and *Associated slices* normalisations are implemented for asymmetric RNA-DNA interactome data and *Iterative correction* is the default normalisation for Hi-C data.

-	*Binomial test*: determines statistical significance of each bin over the genome-wide coverage of the interacting RNA. A slider bar allows to modify the *pAccept* which is the value at which the p-values is accepted as significant. It is possible to select the option to display coverage of the normalisation in the secondary data panel. It is also possible to change the axis in which the normalisation is performed, by default this normalisation is performed row-wise but if the box is ticked the normalisation is performed column-wise. 

<img src="./docs_conf/static/assoc_binom.gif" width=50%>


-	*Associated slices*: normalises each bin by the sum of trans chromatin-associated interactions of the interacting RNA. To compute this normalisation first the RNAs that are chromatin-associated need to be determined. The number of samples and the bin size of those samples to identify the chromatin-associated RNAs can be modified. As default, 1000 samples are taken, and their bin size is 1 kb. (For comprehensive computational explanation of this normalisation see ref Smoother paper). Computing this normalisation for annotated transcripts instead of bins requires the prior filtering by gene annotation on the RNA axis (see section: 4.3.3. Filter). Chromatin-associated RNAs can be determined by selecting the thresholds in the two lower charts. The top chart displays RNA reads per kbp of the samples (genes) ranked by RNA read densities per kbp. The bottom chart displays the maximal DNA reads per kbp of the genomic samples ranked by linked DNA read densities. The interacting RNA from the interactions fulfilling both thresholds will be the chromatin-associated RNAs.
It is possible to select the option to display coverage of the normalisation in the secondary data panel. It is also possible to change the axis in which the normalisation is performed, by default this normalisation is performed row-wise but if the box is ticked the normalisation is performed column-wise. A tick box allows to choose whether to use the minimum number of interactions (intersections) between datasets as background, otherwise the maximum (all chromatin-associated genes from the different datasets) is used. This is relevant because the normalisation is done separately on the datasets, but to make the normalisation match between the datasets, the chromatin-associated genes need to match. A tick box also allows to ignore or consider cis interactions (within same contig).

-	*Iterative correction* (IC): equalises the visibility of the heatmap by making its column and row sums equal to one. A bias value is computed for every slice (column and row) and IC normalisation of the bins is performed by multiplying the bias of each slice to each slice bin. It is possible to filter out slices with more than the given % of empty bins. A tick box allows to Show bias as tracks in the secondary data panels. It is possible to use only the visible region to compute the IC by ticking the Local IC box. The Mad Max filter slider allows to filter out bins for which the log marginal sum is lower than the given value (see [the Cooler github]( https://github.com/open2c/cooler/blob/0f4cf6e21cea50c92334b87c5c6d5759859f4de8/src/cooler/balance.py#L397)). One slider bar allows to set the threshold for *Minimal number of non-zero bins per slice* and another to define *n* for the Manhattan distance to *Ignore first n bins next to the diagonal*.

The *Dist. Dep. Dec.* sub-tab allows to perform a distance dependant decay normalisation by selecting the tick box *Normalise Primary*. The distance dependant decay is computed with the mean of the value for all the bins at the same Manhattan distance for the current contig and it can be displayed on a plot below by ticking the box *Display*. On the plot, each line represents a bin with the beginning being the top left corner and the end, the bottom right corner of the bin. The normalisation is calculated by dividing each bin to this mean. It is important to consider that the further away from the diagonal a bin is in a contig, has less bins at the same Manhattan distance (or none for the edge bin). A slider allows to modify the minimum and maximum number of samples to compute the distance dependant decay. The top and bottom percentiles of samples can be excluded from the normalisation with the *Percentile of samples to keep (%)* slider.

<img src="./docs_conf/static/norm_ice_ddd.gif" width=50%>


The last *Normalise* sub-tab is *Ploidy* and allows normalisation for practical ploidy. Many genomes are aneuploid or comprise high levels of heterozygosity in their chromosomes to the extent that correction for practical ploidy is required in order to not over- or under-represent reads coming from these regions. Smoother can correct for these genomic imbalances by distributing interactions among varying-ploidy contig sets. The *Ploidy* menu comprises several tick boxes and requires uploading a ploidy file.

4.3.2.ploidy.file.example

To perform the ploidy correction *do correct* must be ticked and ticking *use ploidy corrected contigs* will trigger Smoother to use the order of contigs from the ploidy corrected file instead of the genome sizes. The correction considers *n*-ploid contigs as *n* instances and interactions are divided evenly among the instances of the contigs. The correction has several options that can be selected on the following tick boxes:
-	*Remove inter-contig, intra-instance interactions* will remove interactions between two different instances of the same contig.
-	*Keep interactions from contig-pairs that are in the same group* (ABS: I think I get that but what is group? Group of contigs making one chromosome?)
-	*Keep interactions from contig-pairs that never occur in the same group* (ABS: again needs to be explained making clear what is a group)
-	*Remove interactions that are not explicitly kept by the options above*

<img src="./docs_conf/static/ploidy.gif" width=50%>

##### Filter
In the *Filter* tab of Smoother, there are four sub-tabs: *Datapools, Mapping, Coordinates* and *Annotations*.

*Datapools* allows to define the group or condition for every sample and the type of comparison and representation that should be performed among the samples. The *Primary Datapools* table allows to distribute the samples with interactome data displayed on the heatmap in groups by ticking the different pool per sample. The *Secondary Datapools* table allows to select the axis in which the secondary data panel with unidimensional data should be displayed. A dropdown menu allows to *Merge datasets* belonging to the same datapool group by several operations: *sum, minimum, difference* and *mean*. A second dropdown menu *Compare datapools* by enables the selection of options to display the combined datapools: *sum, show first group a, show first group b, substract, difference, divide, minimum and maximum*.

<img src="./docs_conf/static/compare_datasets.png" width=50%>


*Mapping* allows filtering interactions by mapping quality scores of their reads. The mapping quality score represents the confidence of the aligner for the correctness of each alignment. The highest possible score is 254 and the lowest is 0. The bounds and thresholds that can be used to filter the reads correspond to those listed as -m option when running the init command to generate the index, as default the lower bounds are 0, 3 and 30, and the upper bounds are 3, 30 and 255. The bounds for this filter can be selected on the dropdown menus *Mapping Quality: Lower Bound* and *Mapping Quality: Upper Bound*. 

<img src="./docs_conf/static/by_mapping_quality.gif" width=50%>


One key functionality of Smoother is the possibility to analyse regions of high homology and repeats as multi-mapping (ABS: in Smoother you write multi-mapping and in paper multimapping, choose a way and be consistent) reads can be kept. To do so, the smallest possible rectangle enclosing all possible alignments for a multi-mapping read is computed. A dropdown menu allows to select the preferred option to deal with the multi-mapping reads (MMR) in the scenarios that these rectangles are confined within a bin or overlap more than a bin:
- *Count MMR if all mapping loci are within the same bin*. This is the default option. (ABS: in paper in fact you say this is only option if wanting to keep MMR. And from last times we talked I thought that either they are all in same bin and you keep them all or you ignore them, but here there are many more options which are not so clear to me)
- *Count MMR if mapping loci minimum bounding-box overlaps bin*. It is important noticing that this will overrepresent the multi-mapping read as it will be displayed in more than a bin. (ABS: would that be when you display them all so they are over-represented?)
- *Count MMR if bottom left mapping loci is within a bin* (ABS: sorry to always ask about this this would mean even if one mapping loci is on top right outside bin but bottom left is in same bin they are displayed?)
- *Count MMR if top right mapping loci is within a bin* (ABS:same, I don`t want to explain a lie)
- *Ignore MMRs*. Multi-mapping reads are excluded from the analysis.
- *Count MMR if all mapping loci are within the same bin and ignore non-MMRs*. This option allows analysis only of multi-mapping reads that are enclosed in a bin. This option can be useful for exploratory purposes.
- *Count MMR if mapping loci minimum bounding-box overlaps bin and ignore non-MMRs*. This option allows analysis of multi-mapping reads that are not enclosed in a bin. This option can be useful for exploratory purposes.
(ABS: for me, we still would need the option in which if they are not enclosed in a bin they are distributed randomly to one place or another that is the option done also when analysng unidimensional sequencing)
A tick box allows to show multi-mapping reads with incomplete mapping loci lists, which correspond to those that have too many mapping locations to be reported with the given maximum when running the mapping (ABS: in fact in my case I choose with -n option how many to show, there is a default number but one can also choose to show more or less). It is important to notice that displaying these multi-mappers might introduce noise to the heatmap.

<img src="./docs_conf/static/rescue_multimappers.gif" width=50%>

The *Directionality* dropdown menu allows choosing whether to display interaction for which interaction partners map to any or a particular strand. The options are the following:
- *Count pairs where reads map to any strand*
- *Count pairs where reads map to the same strand*
- *Count pairs where reads map to opposite strands*
- *Count pairs where reads map to the forward strand*
- *Count pairs where reads map to the reverse strand*

*Coordinates* allows filtering the regions displayed on the heatmap. The *Minimum Distance from Diagonal* slider allows setting a minimal Manhattan distance by filtering out bins that are closer to the diagonal than the set value in kbp. The dropdown *Annotation Coordinate System* menu allow to select the annotation to use as filter. Only annotations that have been listed on the `-f` option when running the `init` command to generate the index are available, as default the filterable annotation is gene. Two tick boxes allow changing the coordinate system from bins to the filterable annotation for rows and/or columns. The dropdown *Multiple Annotations in Bin* gives four options to deal with bins that comprise multiple annotations:
- *Combine region from first to last annotation*
- *Use first annotation in Bin*
- *Use one prioritized annotation (stable while zoom- and pan-ing)* (ABS:how do you prioritize it? Or does it do it automatically?)
- *Increase number of bins to match number of annotations (might be slow)*


(ABS: I still have to finish this section multiple bins for annotation / active contigs / symmetry)



*Annotations* (ABS: I still have to write this section)

<img src="./docs_conf/static/by_annotation.gif" width=50%>


##### View
(ABS: I still have to write this section)
In the *View* tab of Smoother, there are five sub-tabs: *Color, Panels, Bins, Virtual4C* and *Rendering*.


Color
Panel
Bins

	Remainder bin

4.3.4.remainder_bin.pdf/svg

Extend remainder bin into the next contig. Only visible they are lost for next contig

but that is for the filtering but also for the display when on a zoomed region and changing the bin size no?

I have two figure


For symmetric data, upper triangle can be mirrored to otherwise empty lower triangle interactively on Smoother (in fact this option takes all interactions and displays them in both)



	


Virtual 4C

show all for V4C for example

<img src="./docs_conf/static/v4c.gif" width=50%>

Rendering


### Using the command line interface
All Smoother analyses can also be performed on the command line without the requirement to launch the graphical interface of Smoother. 
#### Set command
Running Smoother analyses without launching the GUI requires the set sub-command to define the values of different parameters.
#### Get command
The get sub-command allows retrieving the value of a parameter for the current/last session of a given index.
#### Export command
It is possible to save the current/last index session to a file with the export sub-command. This corresponds to the function Export of Smoother (see section 4.3.1. File). The interactome data with the settings of the current session can be saves as a TSV text file with the interactions or as a picture in SVG or PNG format.
