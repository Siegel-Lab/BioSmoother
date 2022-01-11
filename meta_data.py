from os import stat
from chr_sizes import *
from linear_data_as_integral import *
import pickle

class MetaData:
    def __init__(self, info):
        self.chr_sizes = None
        self.datasets = []
        self.data_id_by_path = {}
        self.normalizations = []
        self.norm_id_by_path = {}
        self.annotations = {}
        self.info = info

    def set_chr_sizes(self, chr_sizes):
        self.chr_sizes = chr_sizes

    def add_dataset(self, name, path, group_a, num_reads):
        self.datasets.append([name, path, group_a, num_reads])
        self.data_id_by_path[path] = len(self.datasets)-1

    def add_normalization(self, name, path, x_axis, num_reads):
        self.normalizations.append([name, path, x_axis, num_reads])
        self.norm_id_by_path[path] = len(self.normalizations)-1

    def add_annotations(self, annotation_list):
        starts = {}
        ends = {}
        sorted_list = {}
        for name, start, end, info in annotation_list:
            if name not in starts:
                starts[name] = []
                ends[name] = []
                sorted_list[name] = []
            starts[name].append(start)
            ends[name].append(end)
            sorted_list[name].append((start, end, info))
        for name, start_l in starts.items():
            self.annotations[name] = Coverage().set(start_l, ends[name], sorted_list[name])


    def save(self, file_name):
        with open(file_name, "wb") as out_file:
            pickle.dump(self, out_file, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(file_name):
        with open(file_name, "rb") as in_file:
            return pickle.load(in_file)

    def setup(self, main_layout):
        self.chr_sizes.setup(main_layout)
        
        if hasattr(self, "info"):
            main_layout.info_div.text = self.info
        opt = [ (str(idx), data[0]) for idx, data in enumerate(self.datasets)]
        main_layout.group_a.options = opt
        main_layout.group_b.options = opt
        main_layout.group_a.value = [ str(idx) for idx, data in enumerate(self.datasets) if data[2] ]
        main_layout.group_b.value = [ str(idx) for idx, data in enumerate(self.datasets) if not data[2] ]
        opt = [ (str(idx), data[0]) for idx, data in enumerate(self.normalizations)]
        main_layout.norm_x.options = opt
        main_layout.norm_y.options = opt
        main_layout.norm_x.value = [ str(idx) for idx, data in enumerate(self.normalizations) if not data[2] ]
        main_layout.norm_y.value = [ str(idx) for idx, data in enumerate(self.normalizations) if data[2] ]

        main_layout.displayed_annos.options = list(self.annotations.keys())
        main_layout.displayed_annos.value = list(self.annotations.keys())

