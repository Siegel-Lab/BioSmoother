from meta_data import *
from chr_sizes import *
import os
import random
from heatmap_as_r_tree import *
import subprocess
import argparse

## parses file & sets up axis and matrix to have the appropriate size
def parse_heatmap(in_filename):
    with open(in_filename, "r") as in_file_1:
        for line in in_file_1:
            # parse file columns
            read_name, strnd_1, chr_1, pos_1, _, strnd_2, chr_2, pos_2, _2, mapq_1, mapq_2 = line.split()
            # convert number values to ints
            pos_1, pos_2, mapq_1, mapq_2 = (int(x) for x in (pos_1, pos_2, mapq_1, mapq_2))
            pos_1 -= 1
            pos_2 -= 1

            yield read_name, strnd_1, chr_1, pos_1, strnd_2, chr_2, pos_2, mapq_1, mapq_2

def execute(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
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
        yield read_name, chrom, start_pos, map_q

def parse_annotations(annotation_file, axis_start_pos_offset):
    annos = []

    annotation_types = set()
    with open(annotation_file, "r") as in_file_1:
        for line in in_file_1:
            if line[0] == "#":
                continue
            # parse file colum
            chrom, db_name, annotation_type, from_pos, to_pos, _, strand, _, extras, *opt = line.split()
            annotation_types.add(annotation_type)
            annos.append((annotation_type, axis_start_pos_offset[chrom] + int(from_pos),
                                 int(to_pos) + axis_start_pos_offset[chrom]))
    return annos


def preprocess(out_prefix, chr_len_file_name, annotation_filename, interaction_filenames, normalization_filenames):
    if not os.path.exists(out_prefix):
        os.makedirs(out_prefix)
    meta = MetaData()
    print("processing chromosome sizes...")
    meta.set_chr_sizes(ChrSizes(chr_len_file_name))

    if not annotation_filename is None:
        print("processing annotations...")
        meta.add_annotations(parse_annotations(annotation_filename, meta.chr_sizes.chr_start_pos))

    if os.path.isfile(out_prefix + ".heat.db.dat"):
        os.remove(out_prefix + ".heat.db.dat")
    if os.path.isfile(out_prefix + ".heat.db.idx"):
        os.remove(out_prefix + ".heat.db.idx")
    tree = Tree_4(out_prefix + ".heat.db")
    print("processing rna dna interactions...")
    for path, name, group_a in interaction_filenames:
        cnt = 0
        for read_name, _, chr_1, pos_1, _, chr_2, pos_2, mapq_1, mapq_2 in parse_heatmap(path):
            x = meta.chr_sizes.coordinate(pos_1, chr_1) # RNA
            y = meta.chr_sizes.coordinate(pos_2, chr_2) # DNA
            tree.insert(read_name, len(meta.datasets), x, y, min(mapq_1, mapq_2))
            cnt += 1
        meta.add_dataset(name, path, group_a, cnt)

    if os.path.isfile(out_prefix + ".norm.db.dat"):
        os.remove(out_prefix + ".norm.db.dat")
    if os.path.isfile(out_prefix + ".norm.db.idx"):
        os.remove(out_prefix + ".norm.db.idx")
    t_n = Tree_3(out_prefix + ".norm.db")
    print("processing normalizations...")
    for path, name, for_row in normalization_filenames:
        cnt = 0
        for read_name, chrom, start_pos, map_q in parse_norm_file(path):
            x = meta.chr_sizes.coordinate(start_pos, chrom)
            tree.insert(read_name, len(meta.normalizations), x, map_q)
            cnt += 1
        meta.add_normalization(name, path, for_row, cnt)

    meta.save(out_prefix + ".meta")
    print("done")

def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--chr_len', metavar="PATH", required=True)
    parser.add_argument('-o', '--out_prefix', metavar="PATH", required=True)
    parser.add_argument('-i', '--interaction', action='append', nargs=3, metavar=("PATH", "NAME", "GROUP_A"), 
                    required=True)
    parser.add_argument('-n', '--normalization', action='append', nargs=3, metavar=("PATH", "NAME", "FOR_ROW"), 
                    required=True)
    parser.add_argument('-a', '--annotations', metavar="PATH", default=None)
    #parser.add_argument('-h', '--help', help="Display help and exit", default=False)

    args = parser.parse_args()

    preprocess(args.o, args.l, args.a, args.i, args.n)


if __name__ == "__main__":
    parse()