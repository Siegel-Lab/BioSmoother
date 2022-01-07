from meta_data import *
from chr_sizes import *
import os
import random
from heatmap_as_r_tree import *

DEFAULT_OUT = "out/"

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

    l = 100

    def reads():
        s = []
        e = []
        for _ in range(100):
            x = random.choice(range(l-25))
            s.append(x)
            e.append(x+25)
        return s, e
    meta.dna_coverage.set(*reads())
    meta.rna_coverage.set(*reads())

    meta.save(DEFAULT_OUT + name + ".meta")

    os.remove(DEFAULT_OUT + name + ".db.dat")
    os.remove(DEFAULT_OUT + name + ".db.idx")
    t = Tree(DEFAULT_OUT + name + ".db")
    y_r = [*range(l)] + [50]*500
    for i in range(6):
        for _ in range(NUM_READS):
            x = random.choice(range(l))
            y = random.choice(y_r)
            z = random.choice(range(255))
            t.insert("", i, x, y, z)


if __name__ == "__main__":
    preprocess("test", "Lister427.sizes")