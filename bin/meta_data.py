from os import stat
from bin.chr_sizes import *
from bin.linear_data_as_integral import *
import pickle
import sys
import bisect
from bokeh.models import AdaptiveTicker
from bokeh.models import FuncTickFormatter


class MetaData:
    def __init__(self, dividend):
        self.chr_sizes = None
        self.datasets = {}
        self.data_id_by_path = {}
        self.normalizations = {}
        self.norm_id_by_path = {}
        self.annotations = {}
        self.info = ""
        self.norm = {}
        self.dividend = dividend
        self.dist_dep_decay_for_chr = {}

    def add_dist_dep_decay(self, chr_name, x, y):
        self.dist_dep_decay_for_chr[chr_name] = (x, y)

    def get_dist_dep_decay(self, chr_x, x, chr_y, y):
        if chr_x != chr_y:
            return 1
        if chr_x not in self.dist_dep_decay_for_chr:
            return 1
        d = abs(x - y)
        xs, ys = self.dist_dep_decay_for_chr[chr_x]
        idx = bisect.bisect_left(xs, d)
        if idx >= len(xs):
            return ys[-1]
        if idx == 0:
            return ys[0]
        lo = xs[idx - 1]
        hi = xs[idx]
        fac = (d - lo) / (hi - lo)
        assert fac >= 0 and fac <= 1
        lo = ys[idx - 1]
        hi = ys[idx]
        r = lo * (1-fac) + hi * fac
        return r

    def __str__(self):
        datasets_str = "Datasets:\n"
        datasets_str += "id\tname\tgroup\tinput path\twith mapping quality\twith multi mapping\n"
        for idx, (name, path, group_a, map_q, multi_map) in self.datasets.items():
            datasets_str += str(idx) + "\t" + name + "\t" + group_a + "\t" + path + "\t" + map_q + "\t" + multi_map + "\n"
        norms_str = "Normalizations:\n"
        norms_str += "id\tname\twhere\tinput path\twith mapping quality\twith multi mapping\n"
        for idx, (name, path, x_axis, map_q, multi_map) in self.normalizations.items():
            norms_str += str(idx) + "\t" + name + "\t" + x_axis + "\t" + path + "\t" + map_q + "\t" + multi_map + "\n"
        return datasets_str + "\n" + norms_str

    def set_chr_sizes(self, chr_sizes):
        self.chr_sizes = chr_sizes

    def add_dataset(self, name, path, group_a, idx, map_q, multi_map):
        self.datasets[name] = [idx, path, group_a, map_q, multi_map]
        self.data_id_by_path[path] = idx

    def dataset_name_unique(self, name):
        return name in self.dataset

    def add_normalization(self, name, path, x_axis, idx, map_q, multi_map):
        self.normalizations[name] = [idx, path, x_axis, True, map_q, multi_map]
        self.norm_id_by_path[path] = idx

    def normalization_name_unique(self, name):
        return name in self.normalizations

    def add_wig_normalization(self, name, path, x_axis, xs, ys):
        idx = -len(self.normalizations)-1
        self.normalizations[name] = [idx, path, x_axis, False, False, False]
        self.norm_id_by_path[path] = idx
        self.norm[idx] = Coverage().set_x_y(xs, ys)

    def add_annotations(self, annotation_list):
        sorted_list = {}
        for name, start, end, info in annotation_list:
            if name not in sorted_list:
                sorted_list[name] = []
            sorted_list[name].append((start, end, info))
        for name, start_l in sorted_list.items():
            self.annotations[name] = Coverage().set(start_l, self.chr_sizes)


    def save(self, file_name):
        with open(file_name, "wb") as out_file:
            pickle.dump(self, out_file, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(file_name):
        with open(file_name, "rb") as in_file:
            ret = pickle.load(in_file)
            return ret

    def norm_via_tree(self, idx):
        return self.normalizations[idx][3]
    
    
    def get_formatter(self, l):
        ll = []
        idx = 0
        for x, _, _ in l:
            while idx + 1 < len(self.chr_sizes.chr_starts) and x > self.chr_sizes.chr_starts[idx + 1]:
                idx += 1
            ll.append(self.chr_sizes.chr_order[idx][:-len(self.chr_sizes.lcs)] 
                        + ": " + str(x - self.chr_sizes.chr_starts[idx]))
        return FuncTickFormatter(
            args={"l": ll},
            code="""
                if(tick < 0 || tick >= l.length)
                    return "n/a";
                return l[tick];
            """)

    def setup_coordinates(self, main_layout, x_coords_d, y_coords_d):
        ticker_border = AdaptiveTicker(desired_num_ticks=3)
        if x_coords_d != "full_genome":
            main_layout.heatmap.x_range.start = 0
            main_layout.heatmap.x_range.end = self.annotations[x_coords_d].num_reads
            main_layout.heatmap.x_range.reset_start = 0
            main_layout.heatmap.x_range.reset_end = self.annotations[x_coords_d].num_reads
            for plot in [main_layout.heatmap, main_layout.ratio_y, main_layout.raw_y, main_layout.anno_y,
                        main_layout.heatmap_x_axis]:
                plot.xgrid.ticker = ticker_border
                plot.xgrid.bounds = (0, self.annotations[x_coords_d].num_reads)
                plot.xaxis.bounds = (0, self.annotations[x_coords_d].num_reads)
                plot.xaxis.major_label_text_align = "left"
                plot.xaxis.ticker.min_interval = 1
            main_layout.heatmap_x_axis.xaxis[0].formatter = self.get_formatter(self.annotations[x_coords_d].sorted)
        if y_coords_d != "full_genome":
            main_layout.heatmap.y_range.start = 0
            main_layout.heatmap.y_range.end = self.annotations[y_coords_d].num_reads
            main_layout.heatmap.y_range.reset_start = 0
            main_layout.heatmap.y_range.reset_end = self.annotations[y_coords_d].num_reads
            for plot in [main_layout.heatmap, main_layout.ratio_x, main_layout.raw_x, main_layout.anno_x,
                        main_layout.heatmap_y_axis]:
                plot.ygrid.ticker = ticker_border
                plot.ygrid.bounds = (0, self.annotations[y_coords_d].num_reads)
                plot.yaxis.bounds = (0, self.annotations[y_coords_d].num_reads)
                plot.yaxis.major_label_text_align = "right"
                plot.yaxis.ticker.min_interval = 1
            main_layout.heatmap_y_axis.yaxis[0].formatter = self.get_formatter(self.annotations[y_coords_d].sorted)
        self.chr_sizes.setup_coordinates(main_layout, x_coords_d, y_coords_d)

    def setup(self, main_layout):
        self.chr_sizes.setup(main_layout)
        
        main_layout.set_group([d[0] for d in self.datasets.values()], {
            "A": [ data[0] for idx, data in self.datasets.items() if data[2] in ["a", "both"] ],
            "B": [ data[0] for idx, data in self.datasets.items() if data[2] in ["b", "both"] ],
        })

        main_layout.set_norm([d[0] for d in self.normalizations.values()], {
            "Rows": [ data[0] for idx, data in self.normalizations.items() if data[2] in ["row", "both"] ],
            "Columns": [ data[0] for idx, data in self.normalizations.items() if data[2] in ["col", "both"] ]
        })

        main_layout.set_annos(self.annotations.keys(), {
            "Displayed": self.annotations.keys(),
            "Row filter": [],
            "Column filter": []
        })

        possible_coords = [("Genomic loci", "full_genome")]
        for anno_names in self.annotations.keys():
            possible_coords.append((anno_names, anno_names))
        main_layout.x_coords_update(possible_coords)
        main_layout.y_coords_update(possible_coords)

