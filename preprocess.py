import os
os.environ["STXXLLOGFILE"] = "/dev/null"
os.environ["STXXLERRLOGFILE"] = "/dev/null"

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
            pos_1, pos_2, mapq_1, mapq_2 = (
                int(x) for x in (pos_1, pos_2, mapq_1, mapq_2))
            pos_1 -= 1
            pos_2 -= 1

            yield read_name, strnd_1, chr_1, int(pos_1), strnd_2, chr_2, int(pos_2), mapq_1, mapq_2


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

def simplified_filepath(path):
    x = path[path.rindex("/")+1:]
    return x[:x.index(".")]

def parse_annotations(annotation_file, axis_start_pos_offset):
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
            annos.append((annotation_type, axis_start_pos_offset[chrom] + int(from_pos),
                        int(to_pos) + axis_start_pos_offset[chrom], extras.replace(";", "\n")))
    return annos


def parse_wig_file(filename, chr_start_idx):
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
                xs.append(int(a) + chr_start_idx[curr_chr])
                ys.append(float(b))
        xs.append(chr_start_idx['end'])
        ys.append(0)
        yield xs, ys, track

TEST = True
TEST_FAC = 100000

def make_meta(out_prefix, chr_len_file_name, annotation_filename):
    meta = MetaData()
    meta.set_chr_sizes(ChrSizes(chr_len_file_name, filter=lambda x: ("Chr10_" in x) or not TEST))

    if not annotation_filename is None:
        meta.add_annotations(parse_annotations(annotation_filename, meta.chr_sizes.chr_start_pos))

    meta.save(out_prefix + ".meta")


def add_replicate(out_prefix, path, name, group_a):
    meta = MetaData.load(out_prefix + ".meta")
    index = DependantDimSparsePrefixSum_5D(out_prefix, True)
    cnt = 0
    last_cnt = len(index)
    file_size = int(subprocess.run(['wc', '-l', path], stdout=subprocess.PIPE).stdout.decode('utf-8').split(" ")[0])
    file_name = simplified_filepath(path)
    for idx_2, (read_name, _, chr_1, pos_1, _, chr_2, pos_2, mapq_1, mapq_2) in enumerate(parse_heatmap(path)):
        if idx_2 % PRINT_MODULO == 0:
            print("loading file", file_name, ", line", idx_2+1, "of", file_size, "=", 
                    100*(idx_2+1)/file_size, "%", end="\033[K\r")
        if not chr_1 in meta.chr_sizes.chr_sizes:
            continue
        if not chr_2 in meta.chr_sizes.chr_sizes:
            continue
        map_q = min(mapq_1, mapq_2)
        act_pos_1 = meta.chr_sizes.coordinate(pos_2, chr_2)
        act_pos_2 = meta.chr_sizes.coordinate(pos_1, chr_1)
        index.add_point([act_pos_1, act_pos_2, map_q, 0, 0], read_name)
        cnt += 1
        if cnt > TEST_FAC and TEST:
            break
    print("generating index")
    idx = index.generate(last_cnt, cnt + last_cnt)
    meta.add_dataset(name, path, group_a, idx)
    meta.save(out_prefix + ".meta")

def add_normalization(out_prefix, path, name, for_row):
    meta = MetaData.load(out_prefix + ".meta")
    index = SparsePrefixSum_3D(out_prefix + ".norm", True)
    last_cnt = len(index)
    file_size = int(subprocess.run(['samtools', 'view', '-c', path], stdout=subprocess.PIPE).stdout.decode('utf-8'))
    file_name = simplified_filepath(path)
    if path[-4:] == ".wig":
        for xs, ys, n in parse_wig_file(path, meta.chr_sizes.chr_start_pos):
            meta.add_wig_normalization(name + ": " + n, path, for_row, xs, ys)
    else:
        cnt = 0
        for idx_2, (read_name, chrom, pos, map_q) in enumerate(parse_norm_file(path)):
            if idx_2 % PRINT_MODULO == 0:
                print("loading file", file_name, ", line", idx_2+1, "of", file_size, "=", 
                      100*(idx_2+1)/file_size, "%", end="\033[K\r")
            if not chrom in meta.chr_sizes.chr_sizes:
                continue
            act_pos = meta.chr_sizes.coordinate(pos, chrom)
            index.add_point([act_pos, map_q, 0], read_name)
            cnt += 1
            if cnt > TEST_FAC and TEST:
                break
        print("generating index")
        idx = index.generate(last_cnt, cnt + last_cnt)
        meta.add_normalization(name, path, for_row, idx)
    meta.save(out_prefix + ".meta")


def init(args):
    make_meta(args.index_prefix, args.chr_len, args.annotations)

def repl(args):
    add_replicate(args.index_prefix, args.path, args.name, args.group)

def norm(args):
    add_normalization(args.index_prefix, args.path, args.name, args.group)

def grid_seq_norm(args):
    meta = MetaData.load(args.index_prefix + ".meta")
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
        index_arr = PsArray(args.index_prefix + ".norm", True)
        add_as_normalization(filtered_rr, datasets, meta, index, index_arr, args.mapping_q, args.name, 
                             "GRID-seq normalization created with " + str(sys.argv))

    meta.save(args.index_prefix + ".meta")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    sub_parsers = parser.add_subparsers(help='sub-command', dest="cmd")
    sub_parsers.required=True

    init_parser = sub_parsers.add_parser("init")
    init_parser.add_argument('index_prefix')
    init_parser.add_argument('chr_len')
    init_parser.add_argument('-a', '--annotations', metavar="PATH", default=None)
    init_parser.set_defaults(func=init)

    repl_parser = sub_parsers.add_parser("repl")
    repl_parser.add_argument('index_prefix')
    repl_parser.add_argument('path')
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

    args = parser.parse_args()
    args.func(args)

