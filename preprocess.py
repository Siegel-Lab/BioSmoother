import os
import stat as stat_perm
import argparse
from meta_data import *
from chr_sizes import *
import random
import sys
from heatmap_as_r_tree import *
import subprocess
import glob
import math
from libSps import *
from grid_seq_norm import *

PRINT_MODULO = 10000

# parses file & sets up axis and matrix to have the appropriate size


def parse_heatmap(in_filename):
    with open(in_filename, "r") as in_file_1:
        for line in in_file_1:
            # parse file columns
            read_name, strnd_1, chr_1, pos_1, _, strnd_2, chr_2, pos_2, _2, mapq_1, mapq_2 = line.split()
            # convert number values to ints
            pos_1, pos_2, mapq_1, mapq_2 = (int(x) for x in (pos_1, pos_2, mapq_1, mapq_2))
            pos_1 -= 1
            pos_2 -= 1

            yield read_name, strnd_1, chr_1, int(pos_1), strnd_2, chr_2, int(pos_2), mapq_1, mapq_2

def group_heatmap(in_filename, file_size):
    file_name = simplified_filepath(in_filename)
    groups = {}
    for idx_2, (read_name, _, chr_1, pos_1, _, chr_2, pos_2, mapq_1, mapq_2) in enumerate(parse_heatmap(in_filename)):
        map_q = min(mapq_1, mapq_2)
        if not read_name in groups:
            groups[read_name] = []
        groups[read_name].append((chr_1, int(pos_1), chr_2, int(pos_2), int(map_q)))
        
        if idx_2 % PRINT_MODULO == 0:
            print("loading file", file_name, ", line", idx_2+1, "of", file_size, "=", 
                    100*(idx_2+1)/file_size, "%", end="\033[K\r")

    for idx, (read_name, group) in enumerate(groups.items()):
        if idx % PRINT_MODULO == 0:
            print("processing ", file_name, ", read", idx+1, "of", len(groups), "=", 
                    100*(idx+1)/len(groups), "%", end="\033[K\r")
        chr_1 = group[0][0]
        chr_2 = group[0][2]
        for g_chr_1, _, g_chr_2, _, _ in group:
            if g_chr_1 != chr_1:
                continue # no reads that come from different chromosomes
            if g_chr_2 != chr_2:
                continue # no reads that come from different chromosomes
        pos_1_s = min([g[1] for g in group])
        pos_2_s = min([g[3] for g in group])
        pos_1_e = max([g[1] for g in group])
        pos_2_e = max([g[3] for g in group])
        map_q = max([g[4] for g in group])
        yield read_name, chr_1, pos_1_s, pos_1_e, chr_2, pos_2_s, pos_2_e, map_q

def execute(cmd):
    popen = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


def parse_norm_file(filename):
    for line in execute(['samtools', 'view', filename]):
        if len(line) == 0:
            continue
        split = line.split("\t")
        if len(split) < 4:
            print("weird line in bam file: '", line, "'")
            continue

        read_name, flag, chrom, start_pos, map_q, *other = split
        yield read_name, chrom, int(start_pos), int(map_q)

def group_norm_file(in_filename, file_size):
    file_name = simplified_filepath(in_filename)
    groups = {}
    for idx_2, (read_name, chrom, pos, map_q) in enumerate(parse_norm_file(in_filename)):
        if idx_2 % PRINT_MODULO == 0:
            print("loading file", file_name, ", line", idx_2+1, "of", file_size, "=", 
                    100*(idx_2+1)/file_size, "%", end="\033[K\r")
        if not read_name in groups:
            groups[read_name] = []
        groups[read_name].append((chrom, int(pos), int(map_q)))

    for idx, (read_name, group) in enumerate(groups.items()):
        if idx % PRINT_MODULO == 0:
            print("processing ", file_name, ", read", idx+1, "of", len(groups), "=", 
                    100*(idx+1)/len(groups), "%", end="\033[K\r")
        chr_1 = group[0][0]
        for chr_2, _, _ in group:
            if chr_2 != chr_1:
                continue # no reads that come from different chromosomes
        pos_s = min([g[1] for g in group])
        pos_e = max([g[1] for g in group])
        map_q = max([g[2] for g in group])
        yield read_name, chr_1, pos_s, pos_e, map_q

def simplified_filepath(path):
    x = path[path.rindex("/")+1:]
    return x[:x.index(".")]

def parse_annotations(annotation_file, axis_start_pos_offset, dividend):
    annos = []

    annotation_types = set()
    with open(annotation_file, "r") as in_file_1:
        for line in in_file_1:
            if line[0] == "#":
                continue
            # parse file colum
            chrom, db_name, annotation_type, from_pos, to_pos, _, strand, _, extras, *opt = line.split()
            
            if not chrom in axis_start_pos_offset:
                continue
            annotation_types.add(annotation_type)
            s = axis_start_pos_offset[chrom] + int(from_pos) // dividend
            e = int(to_pos) // dividend + axis_start_pos_offset[chrom]
            annos.append((annotation_type, s, max(s+1, e), extras.replace(";", "\n")))
    return annos


def parse_wig_file(filename, chr_start_idx, dividend):
    with open(filename, "r") as in_file_1:
        curr_chr = None
        xs = [0]
        ys = [0]
        track = None
        y = "track"
        x = "variableStep chrom="
        for line in in_file_1.readlines():
            if line[:len(y)] == y:
                if not track is None:
                    xs.append(chr_start_idx['end'])
                    ys.append(0)
                    yield xs, ys, track
                    xs = [0]
                    ys = [0]
                track = line[line.index("name=\"")+len("name=\""):-2]
            elif line[:len(x)] == x:
                curr_chr = line[len(x):line.index(" span=")]
                if not curr_chr in chr_start_idx:
                    print("WIG file contains unknown contig", curr_chr)
                else:
                    xs.append(chr_start_idx[curr_chr])
                    ys.append(0)
            elif curr_chr in chr_start_idx:
                a, b = line[:-1].split(" ")
                xs.append(int(a) // dividend + chr_start_idx[curr_chr])
                ys.append(float(b))
        xs.append(chr_start_idx['end'])
        ys.append(0)
        yield xs, ys, track

TEST_FAC = 100000

def make_meta(out_prefix, chr_len_file_name, annotation_filename, dividend, test=False):
    os.makedirs(out_prefix + ".smoother_index")
    #os.chmod(out_prefix + ".smoother_index", # would make it look more like a file but do i really want that?
    #         stat_perm.S_IWUSR | stat_perm.S_IXUSR | stat_perm.S_IXGRP | stat_perm.S_IXOTH )
    meta = MetaData(dividend)
    meta.set_chr_sizes(ChrSizes(chr_len_file_name, dividend, filter=lambda x: ("Chr10_" in x) or not test))

    if not annotation_filename is None:
        meta.add_annotations(parse_annotations(annotation_filename, meta.chr_sizes.chr_start_pos, dividend))

    meta.save(out_prefix + ".smoother_index/meta")


def add_replicate(out_prefix, path, name, group_a, test=False, cached=False):
    meta = MetaData.load(out_prefix + ".smoother_index/meta")
    index = make_sps_index(out_prefix + ".smoother_index/repl", 3, True, 2, "Cached" if cached else "Disk", True )
    cnt = 0
    last_cnt = len(index)
    file_size = int(subprocess.run(['wc', '-l', path], stdout=subprocess.PIPE).stdout.decode('utf-8').split(" ")[0])
    for read_name, chr_1, pos_1_s, pos_1_e, chr_2, pos_2_s, pos_2_e, map_q in group_heatmap(path, file_size):
        if not chr_1 in meta.chr_sizes.chr_sizes:
            continue
        if not chr_2 in meta.chr_sizes.chr_sizes:
            continue
        act_pos_1_s = meta.chr_sizes.coordinate(pos_2_s // meta.dividend, chr_2)
        act_pos_1_e = meta.chr_sizes.coordinate(pos_2_e // meta.dividend, chr_2)
        act_pos_2_s = meta.chr_sizes.coordinate(pos_1_s // meta.dividend, chr_1)
        act_pos_2_e = meta.chr_sizes.coordinate(pos_1_e // meta.dividend, chr_1)
        index.add_point([act_pos_1_s, act_pos_2_s, map_q], [act_pos_1_e, act_pos_2_e, map_q], read_name)
        cnt += 1
        if cnt > TEST_FAC and test:
            break
    print("generating index")
    idx = index.generate(last_cnt, len(index))
    meta.add_dataset(name, path, group_a, idx)
    meta.save(out_prefix + ".smoother_index/meta")

def add_normalization(out_prefix, path, name, for_row, test=False, cached=False):
    meta = MetaData.load(out_prefix + ".smoother_index/meta")
    index = make_sps_index(out_prefix + ".smoother_index/norm", 2, False, 1, "Cached" if cached else "Disk", True )
    last_cnt = len(index)
    if path[-4:] == ".wig":
        for xs, ys, n in parse_wig_file(path, meta.chr_sizes.chr_start_pos, meta.dividend):
            meta.add_wig_normalization(name + ": " + n, path, for_row, xs, ys)
    else:
        cnt = 0
        file_size = int(subprocess.run(['samtools', 'view', '-c', path], stdout=subprocess.PIPE).stdout.decode('utf-8'))
        for read_name, chrom, pos_s, pos_e, map_q in group_norm_file(path, file_size):
            if not chrom in meta.chr_sizes.chr_sizes:
                continue
            act_pos_s = meta.chr_sizes.coordinate(int(pos_s) // meta.dividend, chrom)
            act_pos_e = meta.chr_sizes.coordinate(int(pos_e) // meta.dividend, chrom)
            index.add_point([act_pos_s, map_q], [act_pos_e, map_q], read_name)
            cnt += 1
            if cnt > TEST_FAC and test:
                break
        print("generating index")
        idx = index.generate(last_cnt, len(index))
        meta.add_normalization(name, path, for_row, idx)
    meta.save(out_prefix + ".smoother_index/meta")


def init(args):
    make_meta(args.index_prefix, args.chr_len, args.annotations, args.dividend, args.test)

def repl(args):
    add_replicate(args.index_prefix, args.path, args.name, args.group, args.test, not args.uncached)

def norm(args):
    add_normalization(args.index_prefix, args.path, args.name, args.group, args.test, not args.uncached)

def grid_seq_norm(args):
    meta = MetaData.load(args.index_prefix + ".smoother_index/meta")
    index = Tree_4(args.index_prefix)
    datasets = args.datasets
    if datasets is None or len(datasets) == 0:
        datasets = list(range(len(meta.datasets)))
    ranked_regions = make_grid_seq_ranked_regions(index, datasets, args.mapping_q, meta.chr_sizes,
                                                  meta.annotations, args.annotation, args.bin_size)
    if args.visualize:
        make_grid_seq_plots(ranked_regions, args.filter_rna, args.filter_dna)
    filtered_rr = filter_r_r(ranked_regions, args.filter_rna, args.filter_dna)[:100]
    if args.add_annotation:
        do_add_annotation(filtered_rr, meta, args.name)
    if args.add_normalization_track:
        index_arr = make_sps_index(args.index_prefix + ".smoother_index/norm", 2, False, 1, "Cached" if args.cached else "Disk", True )
        add_as_normalization(filtered_rr, datasets, meta, index, index_arr, args.mapping_q, args.name, 
                             "GRID-seq normalization created with " + str(sys.argv))

    meta.save(args.index_prefix + ".smoother_index/meta")

def get_argparse():
    parser = argparse.ArgumentParser(description='Create indices for the smoother Hi-C data viewer.')

    ## deebugging arguments
    parser.add_argument('--test', help=argparse.SUPPRESS, action='store_true')
    parser.add_argument('--uncached', help=argparse.SUPPRESS, action='store_true')

    sub_parsers = parser.add_subparsers(help='Sub-command that shall be executed.', dest="cmd")
    sub_parsers.required=True

    init_parser = sub_parsers.add_parser("init", help="Create a new index.")
    init_parser.add_argument('index_prefix', 
        help="Path where the index shall be saved. Note: a folder with multiple files will be created.")
    init_parser.add_argument('chr_len', 
        help="Path to a file that contains the length (in nucleotides) of all chromosomes. The file shall contain 2 tab seperated columns columns: The chromosome names and their size in nucleotides. The order of chromosomes in this files will be used as the display order in the viewer.")
    init_parser.add_argument('-d', '--dividend', type=int, default=1,
        help="Divide all coordinates by this number. Larger numbers will reduce the index size and preprocessing time. However, bins with a size below this given number cannot be displayed.")
    init_parser.add_argument('-a', '--annotations', metavar="PATH", default=None,
        help="Path to a file that contains annotations for the genome. File should be in the gff3 fromat.")
    init_parser.set_defaults(func=init)

    repl_parser = sub_parsers.add_parser("repl", help="Add a replicate to a given index.")
    repl_parser.add_argument('index_prefix', 
        help="Prefix that was used to create the index (see the init subcommand).")
    repl_parser.add_argument('path', 
        help="Path to the .pre1.bed file that contains the aligned reads.")
    repl_parser.add_argument('name')
    repl_parser.add_argument('-g', '--group', default="neither", choices=["a", "b", "both", "neither"], 
                            help="(default: %(default)s)")
    repl_parser.set_defaults(func=repl)

    norm_parser = sub_parsers.add_parser("norm")
    norm_parser.add_argument('index_prefix')
    norm_parser.add_argument('path')
    norm_parser.add_argument('name')
    norm_parser.add_argument('-g', '--group', default="neither", 
                             choices=["row", "col", "both", "neither"], help="(default: %(default)s)")
    norm_parser.set_defaults(func=norm)

    grid_seq_norm_parser = sub_parsers.add_parser("grid-seq-norm")
    grid_seq_norm_parser.add_argument('index_prefix')
    grid_seq_norm_parser.add_argument('name')
    grid_seq_norm_parser.add_argument('-d', '--datasets', metavar="VAL", nargs='*', type=int)
    grid_seq_norm_parser.add_argument('-m', '--mapping_q', metavar="VAL", type=int, default=0)
    grid_seq_norm_parser.add_argument('-b', '--bin_size', metavar="VAL", type=int, default=1000)
    grid_seq_norm_parser.add_argument('-R', '--filter_rna', metavar="VAL", type=float, default=100)
    grid_seq_norm_parser.add_argument('-D', '--filter_dna', metavar="VAL", type=float, default=10)
    grid_seq_norm_parser.add_argument('-A', '--annotation',
            help="name of the annotation to use as bins for the RNA or 'bins' to use --bin_size sized bins over the full genome", 
            metavar="VAL", default="gene")
    grid_seq_norm_parser.add_argument('-v', '--visualize', action='store_true')
    grid_seq_norm_parser.add_argument('-a', '--add_annotation', action='store_true')
    grid_seq_norm_parser.add_argument('-n', '--add_normalization_track', action='store_true')
    grid_seq_norm_parser.set_defaults(func=grid_seq_norm)

    return parser

if __name__ == "__main__":
    parser = get_argparse()

    args = parser.parse_args()

    args.func(args)

