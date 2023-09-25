## The Datastructure

Smoother uses a datastructure called libSps implemented in C++ for querying the interactions as effectiveley as possible.
You can find the [GitHub of libSps here](https://github.com/MarkusRainerSchmidt/libSps "Go to the libSps GitHub").

### Algorithmic Description

libSps provides several features that make it possible to bin, normalize and visualize nucleic acid interaction data on-the-fly.
In brief, these are:

- F1: Looking up the number of interactions within any rectangle in constant time (i.e. the lookup time is independent of the total number of interactions and the number of interactions in the rectangle)
- F2: During this lookup, interactions can be filtered for mapping quality (again this is done in constant time)
- F3: libSps can distinguish between interactions that map to multiple consecutive loci and multiple distributed loci (we want to count the first but exclude the latter)
- F4: The memory requirements for libSps are optimized

#### F1: Constant lookup times

libSps uses a technique called prefix sums [1] for storing interaction counts.
With prefix sums, each cell in a matrix stores the number of interactions that can be found to its bottom-left. 

<img src="docs_conf/static/algorithmics_desc/2d-prefix-sum.png" />

*Example prefix sum matrix.* The left picture shows the positions of individual points. The middle picture shows the matrix entries after prefix sums have been computed for the y-dimension. The right picture shows the matrix entries after prefix sums have been computed for the x and y dimension.

Once the prefix sums have been computed, looking up the entry at a position x/y returns the number of points between 0/0 and x/y. 
By looking up 4 entries and adding their values together, we can query and arbitrary rectangle.
This lookup is extremely fast, as it is independent of the total number of interactions and the number of interactions in the queried rectangle.

<img src="docs_conf/static/algorithmics_desc/2d-prefix-sum-query.png" />

*Querying a prefix sum matrix.* Four lookups are needed, one lookup positioned at each corner of the queried rectangle. The top-left and bottom-right corner values are subtracted from the value at the top-right to exclude the area to the left and bottom of the queried rectangle (left), respectiveley. This subtracts the area to the bottom-left of the queried rectangle twice. To make up this difference the value of the bottom-left corner lookup is added to the previous result.

This approach enables us to count the number of interactions in any bin on-the-fly.
In turn, this makes it possible to have varying bin-sizes and normalizations.

#### F2: Filtering for mapping quality

Smoother has a slider to dynamically filter out reads with too low or high mapping qualities. 
Mapping qualities are scores that express an aligners confidence that the read was mapped correctly.
For each interaction (i.e. read-pair with a mapping quality), we place the point at a height according to the mapping quality of the reads.
If both reads have different mapping qualities, we use the lower value.

Then we query cubes instead of rectangles, where the bottom and top of the cubes are defined by the mapping quality slider.

<img src="docs_conf/static/algorithmics_desc/mapq-filter.png" width="50%" />

*Filtering mapping qualities using a 3rd dimension.*

#### F3: Interactions that map to multiple consecutive loci

Genomes have many forms of repetition. 
For example, In *Trypanosome brucei*, the organism we study, genes are often placed in arrays.
I.e. there are many immediateley consecutive copies of the same gene on the genome.
Interactions that map to one of these genes will most likely map to all copies of that gene.
Often, a bin will span over the entirety of such a gene array.
In this case, we want to count interactions that map to all genes in the array towars the bin, as, no matter which gene copy the interaction truly originates from, we know that it originates from within the bin.
In other cases, where an interaction maps to several positions in different bins, we cannot decide which bin to count the interaction towards and therefore filter out the interaction instead.

In the following, we show how we solve the above problem.

First, instead of storing the prefix sums for individual interaction points, we summarize all mapping positions of each interaction into one rectangle.
Here, the rectangle is placed so that it encompasses all mapping positions.

<img src="docs_conf/static/algorithmics_desc/multiple-loci-in-one-bin.png" width="50%" />

*Interaction with multiple mapping positions turned into an rectangle.*

We then compute prefix sum matrices seperately for all four corners of the rectangle.
In the following, we go down to Intervals (i.e. 1-dimensional rectangles) for a simpler example, but in principle everything works the same in the 2-dimensional or n-dimensional case.

To count the number of intervals between a given start and end position, we look up the number of intervals that end before the given end position and the number of intervals that start before the given start position.
Then we substract the latter from the former to receive our count.
Both lookups can be done in constant time using the two prefix sum matrices.

<img src="docs_conf/static/algorithmics_desc/counting-intervals.png" width="50%" />

*Counting intervals instead of points using prefix sum matrices.*

This strategy works fine as long as there is no interval that completely encloses our query region.

<img src="docs_conf/static/algorithmics_desc/too-large-intervals.png" width="50%" />

*Too large intervals break our strategy.*

However, we already developed a strategy for filtering out interactions based on a single numerical property: See F2 - Filtering for mapping quality.
We hence reuse this strategy, placing the rectangles at a position given bey their width and height in a 4th and 5th dimension.
Again, we can then use the bottom and top positions of our 5d-orthotope queries (5-dimensional "cubes") to filter out all rectangles that are too wide or high.

<img src="docs_conf/static/algorithmics_desc/rectangle-width.png" width="50%" />

*Adding two more dimensions to filter rectangle width and height.*

#### F4: Optimizing memory requirements

The strategy, as described above, would not be feasible as the required matrices are simply too large to be stored or computed.
For example, we work with a genome assembly of *Trypanosome brucei* that contains 50,081,021 nucleotides.
Rather small considering e.g. the size of the human genome.
Even so, a genome x genome x mapping confidence matrix is of size 50,081,021^2 * 256 = 583,964 Terrabytes (even if each prefix sum could be stored in a single byte).
This is obviously completely unrealistic and will fit on any hard drive.

We hence use a customized version of a strategy called "sparse prefix sums" by Shekelyan et al. [1] to reduce the index size. We give a quick summary of the part of their method that is relevant to us:

They remove empty rows and columns from point matrices using lookup tables:

<img src="docs_conf/static/algorithmics_desc/sparse-matrices.png" />

*Removing slices. Image taken from [1]*

However, this strategy breaks down for large datasets. 
To split too large datasets down into smaller ones they use overlays.

<img src="docs_conf/static/algorithmics_desc/sparse-matrices-in-large-datasets.png" />

*Left: eventhough the matrix is sparse, there are no empty columns and rows. Right: by splitting the matrix into four submatrices, empty columns and rows can be removed again.*

However, if we now compute the prefix sum for the individual submatrices we loose the ability to query arbitrary rectangles over our dataset.
To fix this, each overlay stores an additional first column and first row that holds the prefix sums of the entire dataset for those positions.
By then querying 

- one position on the additional column, 
- one on the additional row, 
- one on the additional bottom-left corner
- and one inside the overlay 

the prefix sum of arbitrary points can be queried again.

<img src="docs_conf/static/algorithmics_desc/querying-overlays.png" />

*Querying overlays.*

Combined with the querying technique in "F1: Constant lookup times" this gives us the ability to query arbitrary rectangles again.

So much for the technique of Shekelyan et al. [1].
With our dataset, we, however, ran into problems using this technique.
Overlays work best if points are evenly distributed among them.
Imagine a worst case, where all points are within the same overlay.
In that case we still pay the memory we would require for storing the points without overlays, but additionally have to store the remaining empty overlays.

Unfortunately, for our data we come close to this worst case.
Nucleic acid interactome data is heavily clustered along the 45-degree diagonal.
We found that there was no adequate overlay size tradeoff.
Either there would be too many empty overlays to store or the overlays on the diagonal would contain matrices that were too large to store.

Hence, we developed a strategy to distribute overlays better.
We break the grid-like organization of overlays and compute overlay height independently for each column.
We do this via the same lookup table strategy used for removing empty matrix columns and rows.
Here we use the lookup table in dimension 1 first.
Dimension 2 then has an individual lookuptable for each column of dimension 1. Here, the lookup of dimension 1 determines the used lookup table used for dimension 2.
This finally gives us a position in the materialized overlay grid.

<img src="docs_conf/static/algorithmics_desc/distributing-overlays.png" />

*Overlay organization for nucleic acid interactome data.*

### Fileformat specification

Smoothers preprocessing creates several files.
In brief, these files contain the following information:

| file | desc |
|------|------|
| .desc | The description of all points. |
| .points | The coordinates of all points. |
| .prefix_sums | The prefix sum for one position in space. |
| .coords | The translation from real to sparse coordinates. |
| .overlays | The overlay grid. |
| .datasets | The individual datasets. |
| meta | Some metadata about the index. |

Apart from the meta file, all files exist once for the interaction and once for the normalization data.

The exact content of these files is described [here](https://github.com/MarkusRainerSchmidt/libSps "Go to the libSps GitHub").

### Implementation Details

#### Libraries

Smoother is implemented in two separate parts:
- A Python 3 project that handles data visualization and normalization.
- A C++ library that deals with the interaction counting and filesystem.

The python project uses bokeh [5] to create an interactive viewer.
The C++ library uses pybind 11 [6] to create an interface for the python project and stxxl [7] for having access to a cached vector implementation.

#### Runtime benchmarking

#### Verification of Normalizations