from bisect import bisect_left
import enum
from bokeh.plotting import figure, save, output_file
from bisect import bisect_left

def index_count(index, dataset, x_from, x_to, y_from, y_to, map_q_layer, on_rna):
    if on_rna:
        return index.count(dataset, y_from, y_to, x_from, x_to, map_q_layer)
    else:
        return index.count(dataset, x_from, x_to, y_from, y_to, map_q_layer)

def compute_anno_reads(index, datasets, anno_from, anno_to, genome_size, map_q_layer, on_rna=True):
    cnt = 0
    for dataset in datasets:
        cnt += 1000 * index_count(index, dataset, anno_from, anno_to, 0, genome_size, map_q_layer, on_rna) / genome_size
    return cnt / len(datasets)

def compute_anno_reads_binned(index, datasets, anno_from, anno_to, bins, map_q_layer, on_rna=False):
    cnt = 0
    for dataset in datasets:
        for start, size in bins:
            cnt = max(cnt, 1000 * index_count(index, dataset, anno_from, anno_to, 
                                              start, start + size, map_q_layer, on_rna) / size)
    return cnt

def rank_regions(index, datasets, regions, chr_sizes, map_q_layer, bins_size=1000):
    ranked_regions = []
    binned_genome = chr_sizes.bin_cols_or_rows(bins_size, produce_smaller_bins=False)[0]
    for start, size, info in regions:
        ranked_regions.append((
            compute_anno_reads(index, datasets, start, start + size, chr_sizes.chr_start_pos["end"], map_q_layer),
            compute_anno_reads_binned(index, datasets, start, start + size, binned_genome, map_q_layer), 
            start, 
            size,
            info))
    return ranked_regions

def one_dim_plot(ranked_regions, index, y_axis_label, title, filter, color="red", x_axis_label="Ranked by reads RPK"):
    output_file(title.replace(" ", "_").lower() + ".html", title=title)
    ranked_regions.sort(key=lambda x: x[index], reverse=True)
    f = figure(title=title, y_axis_type="log")
    f.yaxis.axis_label = y_axis_label
    f.xaxis.axis_label = x_axis_label
    f.sizing_mode = "stretch_both"
    l = sum(1 if x[index] >= filter else 0 for x in ranked_regions)
    f.dot(x=list(range(l)), y=[x[index] for x in ranked_regions if x[index] >= filter], color=color)
    f.dot(x=[l+x for x in range(len(ranked_regions) - l)], y=[x[index] for x in ranked_regions if x[index] < filter],
            color="black")
    save(f)

def two_dim_plot(ranked_regions, filter_rna, filter_dna):
    output_file("ranking_rna_dna.html", title="Ranking RNA-DNA")
    f = figure(title="Ranking RNA-DNA", y_axis_type="log", x_axis_type="log")
    f.yaxis.axis_label = "Maximal DNA reads in binned genome (RPK)"
    f.xaxis.axis_label = "RNA reads per kb"
    f.sizing_mode = "stretch_both"
    def dot(fil, col):
        f.dot(x=[x[0] for x in ranked_regions if fil(x)], y=[x[1] for x in ranked_regions if fil(x)], color=col)
    dot(lambda r: r[0] < filter_rna and r[1] < filter_dna, "black")
    dot(lambda r: r[0] >= filter_rna and r[1] < filter_dna, "red")
    dot(lambda r: r[0] < filter_rna and r[1] >= filter_dna, "blue")
    dot(lambda r: r[0] >= filter_rna and r[1] >= filter_dna, "purple")
    save(f)

def make_grid_seq_plots(ranked_regions, filter_rna, filter_dna):
    one_dim_plot(ranked_regions, 0, "RNA reads per kb", "Ranking RNA", filter_rna)
    one_dim_plot(ranked_regions, 1, "Maximal DNA reads in binned genome (RPK)", "Ranking DNA", filter_dna, "blue")
    two_dim_plot(ranked_regions, filter_rna, filter_dna)

def make_grid_seq_ranked_regions(index, datasets, map_q_layer, chr_sizes, annotations, 
                                  annotation="gene", bins_size=1000):
    if annotation == "bins":
        binned_genome = [(p, s, "bin [" + str(p) + ", " + str(p+s) + ")")
                         for p, s in chr_sizes.bin_cols_or_rows(bins_size, produce_smaller_bins=False)[0]]
    else:
        binned_genome = annotations[annotation].sorted
    return rank_regions(index, datasets, binned_genome, chr_sizes, map_q_layer, bins_size)

def filter_r_r(ranked_regions, filter_rna, filter_dna):
    return [(start, size, info) for x, y, start, size, info in ranked_regions if x >= filter_rna and y >= filter_dna]

def do_add_annotation(ranked_regions, meta, name):
    meta.add_annotations([(name, start, start + size, info) for start, size, info in ranked_regions])

def add_as_normalization(ranked_regions, datasets, meta, index, index_arr, map_q_layer, name, info):
    idx = meta.add_normalization(name, info, True)

    for dataset in datasets:
        for start, size, info in ranked_regions:
            chr_idx = bisect_left(meta.chr_sizes.chr_starts, start)
            chr_start = meta.chr_sizes.chr_starts[chr_idx]
            chr_size = meta.chr_sizes.chr_sizes_l[chr_idx]
            for x in [
                index.get(dataset, start, start + size, 0, chr_start),
                index.get(dataset, start, start + size, chr_start + chr_size, meta.chr_sizes.chr_start_pos["end"])
            ]:
                for layer, d in enumerate(x):
                    if layer >= map_q_layer:
                        for (pos_x, _), read_name in d:
                            index_arr.add_point(idx, pos_x, layer, read_name + "; dataset: " + str(dataset))

    index_arr.generate()