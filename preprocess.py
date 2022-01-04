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

    meta.save(DEFAULT_OUT + name + "meta")

    t = Tree(DEFAULT_OUT + name + ".db")
    for _ in range(100):
        x = random.choice(range(100))
        y = random.choice(range(100))
        z = random.choice(range(255))
        t.insert("", x, y, z)

if __name__ == "__main__":
    preprocess("test", "Lister427.sizes")