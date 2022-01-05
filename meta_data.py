from os import stat
from chr_sizes import *
import pickle

class MetaData:
    def __init__(self):
        self.chr_sizes = None
        self.datasets = []

    def set_chr_sizes(self, chr_sizes):
        self.chr_sizes = chr_sizes

    def add_dataset(self, name, desc, group_a, num_reads):
        self.datasets.append([name, desc, group_a, num_reads])

    def save(self, file_name):
        with open(file_name, "wb") as out_file:
            pickle.dump(self, out_file, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(file_name):
        with open(file_name, "rb") as in_file:
            return pickle.load(in_file)

    def setup(self, main_layout):
        self.chr_sizes.setup(main_layout)

        main_layout.group_a.options = [ (str(idx), data[0]) for idx, data in enumerate(self.datasets)]
        main_layout.group_a.value = [ str(idx) for idx, data in enumerate(self.datasets) if data[2] ]

