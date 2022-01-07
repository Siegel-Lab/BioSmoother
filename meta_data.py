from os import stat
from chr_sizes import *
from linear_data_as_integral import *
import pickle

class MetaData:
    def __init__(self):
        self.chr_sizes = None
        self.datasets = []
        self.dna_coverage = Coverage()
        self.rna_coverage = Coverage()
        self.annotations = {}

    def set_chr_sizes(self, chr_sizes):
        self.chr_sizes = chr_sizes

    def add_dataset(self, name, desc, group_a, num_reads):
        self.datasets.append([name, desc, group_a, num_reads])

    def add_annotations(self, annotation_list):
        starts = {}
        ends = {}
        for name, start, end in annotation_list:
            if name not in starts:
                starts[name] = []
                ends[name] = []
            starts[name].append(start)
            ends[name].append(end)
        for name, start_l in starts.items():
            self.annotations[name] = Coverage().set(start_l, ends[name])


    def save(self, file_name):
        with open(file_name, "wb") as out_file:
            pickle.dump(self, out_file, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(file_name):
        with open(file_name, "rb") as in_file:
            return pickle.load(in_file)

    def setup(self, main_layout):
        self.chr_sizes.setup(main_layout)

        opt = [ (str(idx), data[0]) for idx, data in enumerate(self.datasets)]
        main_layout.group_a.options = opt
        main_layout.group_b.options = opt
        main_layout.group_a.value = [ str(idx) for idx, data in enumerate(self.datasets) if data[2] ]
        main_layout.group_b.value = [ str(idx) for idx, data in enumerate(self.datasets) if not data[2] ]

        main_layout.displayed_annos.options = list(self.annotations.keys())
        main_layout.displayed_annos.value = list(self.annotations.keys())

