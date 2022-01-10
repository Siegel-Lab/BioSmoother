from meta_data import *
from chr_sizes import *
import os
import random
from heatmap_as_r_tree import *
import subprocess

DEFAULT_OUT = "out/"

## parses file & sets up axis and matrix to have the appropriate size
def parse_heatmap(in_filenames):
    for in_filename in in_filenames.split(","):
        with open(in_filename, "r") as in_file_1:
            for line in in_file_1:
                # parse file columns
                read_name, strnd_1, chr_1, pos_1, _, strnd_2, chr_2, pos_2, _2, mapq_1, mapq_2 = line.split()
                # convert number values to ints
                pos_1, pos_2, mapq_1, mapq_2 = (int(x) for x in (pos_1, pos_2, mapq_1, mapq_2))
                pos_1 -= 1
                pos_2 -= 1

                yield in_filename, read_name, strnd_1, chr_1, pos_1, strnd_2, chr_2, pos_2, mapq_1, mapq_2

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

def insert_heatmap_files(meta, tree, in_filenames):
    for in_filename, read_name, strnd_1, chr_1, pos_1, strnd_2, chr_2, pos_2, mapq_1, mapq_2 in parse_heatmap(in_filenames):
        x = meta.chr_sizes.coordinate(pos_1, chr_1) # RNA
        y = meta.chr_sizes.coordinate(pos_2, chr_2) # DNA
        tree.insert(read_name, meta.data_id_by_path[in_filename], x, y, min(mapq_1, mapq_2))

def preprocess(name, chr_len_file_name):
    if not os.path.exists(DEFAULT_OUT):
        os.makedirs(DEFAULT_OUT)
    meta = MetaData()
    meta.set_chr_sizes(ChrSizes(chr_len_file_name))

    NUM_READS = 1000
    meta.add_dataset("b1r1", "n/a", True, NUM_READS)
    meta.add_dataset("b1r2", "n/a", True, NUM_READS)
    meta.add_dataset("b1r3", "n/a", True, NUM_READS)
    meta.add_dataset("b2r1", "n/a", False, NUM_READS)
    meta.add_dataset("b2r2", "n/a", False, NUM_READS)
    meta.add_dataset("b2r3", "n/a", False, NUM_READS)

    meta.add_normalization("norm_rna", "n/a", False, NUM_READS)
    meta.add_normalization("norm_dna", "n/a", True, NUM_READS)

    l = 100

    def reads():
        s = []
        e = []
        for _ in range(100):
            x = random.choice(range(l-25))
            s.append(x)
            e.append(x+25)
        return s, e

    if os.path.isfile(DEFAULT_OUT + name + ".norm.db.dat"):
        os.remove(DEFAULT_OUT + name + ".norm.db.dat")
    if os.path.isfile(DEFAULT_OUT + name + ".norm.db.idx"):
        os.remove(DEFAULT_OUT + name + ".norm.db.idx")
    t_n = Tree_3(DEFAULT_OUT + name + ".norm.db")
    for i in range(2):
        for _ in range(NUM_READS):
            x = random.choice(range(l))
            z = random.choice(range(255))
            t_n.insert("", i, x, z)

    meta.add_annotations([("a", 5, 15), ("a", 20, 30), ("b", 20, 30), ("b", 40, 43)])
    print(meta.annotations["a"].xs)
    print(meta.annotations["a"].yys)

    meta.save(DEFAULT_OUT + name + ".meta")

    if os.path.isfile(DEFAULT_OUT + name + ".heat.db.dat"):
        os.remove(DEFAULT_OUT + name + ".heat.db.dat")
    if os.path.isfile(DEFAULT_OUT + name + ".heat.db.idx"):
        os.remove(DEFAULT_OUT + name + ".heat.db.idx")
    t = Tree_4(DEFAULT_OUT + name + ".heat.db")
    y_r = [*range(l)] + [50]*500
    for i in range(6):
        for _ in range(NUM_READS):
            x = random.choice(range(l))
            y = random.choice(y_r)
            z = random.choice(range(255))
            t.insert("", i, x, y, z)


if __name__ == "__main__":
    preprocess("test", "Lister427.sizes")