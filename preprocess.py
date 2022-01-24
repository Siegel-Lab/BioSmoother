from meta_data import *
from chr_sizes import *
import os
import random
from heatmap_as_r_tree import *
import subprocess
import argparse

PRINT_MODULO = 100000

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

            yield read_name, strnd_1, chr_1, pos_1, strnd_2, chr_2, pos_2, mapq_1, mapq_2


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


def preprocess(arguments, out_prefix, chr_len_file_name, annotation_filename, interaction_filenames,
               normalization_filenames):
    if "/" in out_prefix:
        out_folder = out_prefix[:out_prefix.rfind("/")]
        if not os.path.exists(out_folder):
            os.makedirs(out_folder)
    meta = MetaData(arguments)
    print("(step 1 of 8) loading chromosome sizes...\t\t\t\t\t")
    meta.set_chr_sizes(ChrSizes(chr_len_file_name))
    dna_bins = [-1] + [int(x) for (x, _) in meta.chr_sizes.bin_cols_or_rows(
        100000)[0]] + [meta.chr_sizes.chr_start_pos["end"]]

    if not annotation_filename is None:
        print("(step 2 of 8) loading annotations...\t\t\t\t\t")
        meta.add_annotations(parse_annotations(
            annotation_filename, meta.chr_sizes.chr_start_pos))

    print("(step 3 of 8) loading interactions...\t\t\t\t\t")
    data = []
    for idx, (path, name, group_a) in enumerate(interaction_filenames):
        cnt = 0
        data.append([len(meta.datasets), []])
        for idx_2, (read_name, _, chr_1, pos_1, _, chr_2, pos_2, mapq_1, mapq_2) in enumerate(parse_heatmap(path)):
            if idx_2 % PRINT_MODULO == 0:
                print("file", idx+1, "of", len(interaction_filenames),
                      ", line", idx_2+1, end="\t\t\t\t\t\r")
            rna_pos = meta.chr_sizes.coordinate(pos_1, chr_1)  # RNA
            dna_pos = meta.chr_sizes.coordinate(pos_2, chr_2)  # DNA
            map_q = min(mapq_1, mapq_2)
            data[-1][1].append([[map_q, rna_pos, dna_pos], read_name])
            cnt += 1
            if cnt > 1000:
                break
        meta.add_dataset(name, path, group_a, cnt)
    print("(step 4 of 8) processing interactions...\t\t\t\t\t")
    tree = Tree_4(data, [list(range(256)), dna_bins, dna_bins])
    print("(step 5 of 8) creating interaction cache...\t\t\t\t\t")

    data = []
    print("(step 6 of 8) loading normalizations...\t\t\t\t\t")
    for idx, (path, name, for_row) in enumerate(normalization_filenames):
        if path[-4:] == ".wig":
            for xs, ys, n in parse_wig_file(path, meta.chr_sizes.chr_start_pos):
                meta.add_wig_normalization(
                    name + ": " + n, path, for_row, xs, ys)
        else:
            cnt = 0
            data.append([len(meta.normalizations), []])
            for idx_2, (read_name, chrom, start_pos, map_q) in enumerate(parse_norm_file(path)):
                if idx_2 % PRINT_MODULO == 0:
                    print("file", idx+1, "of", len(normalization_filenames),
                          ", line", idx_2+1, end="\t\t\t\t\t\r")
                pos = meta.chr_sizes.coordinate(start_pos, chrom)
                data[-1][1].append([[map_q, pos], read_name])
                cnt += 1
                if cnt > 1000:
                    break
            meta.add_normalization(name, path, for_row, cnt)
    print("(step 7 of 8) processing normalizations...\t\t\t\t\t")
    t_n = Tree_3(data, [list(range(256)), dna_bins])
    print("(step 8 of 8) creating normalization cache...\t\t\t\t\t")

    print("done\t\t\t\t\t")
    return meta, tree, t_n


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--chr_len', metavar="PATH", required=True)
    parser.add_argument('-o', '--out_prefix', metavar="PATH", required=True)
    parser.add_argument('-i', '--interaction', action='append', nargs=3, metavar=("PATH", "NAME", "GROUP"),
                        required=True)
    parser.add_argument('-n', '--normalization', action='append', nargs=3, metavar=("PATH", "NAME", "GROUP"),
                        required=True)
    parser.add_argument('-a', '--annotations', metavar="PATH", default=None)

    args = parser.parse_args()

    preprocess('\n'.join(f'{k}={v}' for k, v in vars(args).items()),
               args.out_prefix, args.chr_len, args.annotations, args.interaction, args.normalization)
