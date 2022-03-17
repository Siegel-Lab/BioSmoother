from os import stat
from chr_sizes import *
from linear_data_as_integral import *
import pickle
import bisect
from bokeh.models import AdaptiveTicker
from libKdpsTree import *


class MetaData:
    def __init__(self, mapping_quality_layers):
        self.chr_sizes = None
        self.datasets = []
        self.data_id_by_path = {}
        self.normalizations = []
        self.norm_id_by_path = {}
        self.annotations = {}
        self.info = ""
        self.norm = {}
        assert len(mapping_quality_layers) == SETTINGS.NUM_LAYERS
        self.mapping_quality_layers = mapping_quality_layers

    def get_layer_for_mapping_q(self, layer):
        return bisect.bisect_right(self.mapping_quality_layers, layer)

    def set_chr_sizes(self, chr_sizes):
        self.chr_sizes = chr_sizes

    def add_dataset(self, name, path, group_a):
        self.datasets.append([name, path, group_a])
        self.data_id_by_path[path] = len(self.datasets)-1
        return len(self.datasets)-1

    def add_normalization(self, name, path, x_axis):
        self.normalizations.append([name, path, x_axis])
        self.norm_id_by_path[path] = len(self.normalizations)-1
        return len(self.normalizations)-1

    def add_wig_normalization(self, name, path, x_axis, xs, ys):
        self.normalizations.append([name, path, x_axis, 0])
        self.norm_id_by_path[path] = len(self.normalizations)-1
        self.norm[len(self.normalizations)-1] = Coverage().set_x_y(xs, ys)

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
            self.annotations[name] = Coverage().set(start_l, ends[name], sorted_list[name], self.chr_sizes)


    def save(self, file_name):
        with open(file_name, "wb") as out_file:
            pickle.dump(self, out_file, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(file_name):
        with open(file_name, "rb") as in_file:
            ret = pickle.load(in_file)
            return ret

    def norm_via_tree(self, idx):
        return self.normalizations[idx][1][-4:] == ".bam"

    def setup_coordinates(self, main_layout, show_grid_lines, x_coords_d, y_coords_d):
        ticker_border = AdaptiveTicker()
        c = "lightgrey" if show_grid_lines else None
        c2 = None
        if x_coords_d != "full_genome":
            main_layout.heatmap.x_range.start = 0
            main_layout.heatmap.x_range.end = self.annotations[x_coords_d].num_reads
            main_layout.heatmap.x_range.reset_start = 0
            main_layout.heatmap.x_range.reset_end = self.annotations[x_coords_d].num_reads
            for plot in [main_layout.heatmap, main_layout.ratio_y, main_layout.raw_y, main_layout.anno_y,
                        main_layout.heatmap_x_axis]:
                plot.xgrid.minor_grid_line_alpha = plot.ygrid.grid_line_alpha
                plot.xgrid.minor_grid_line_color = plot.xgrid.grid_line_color
                plot.xgrid.grid_line_color = c
                plot.xgrid.minor_grid_line_color = c2
                plot.xgrid.ticker = ticker_border
                plot.xgrid.bounds = (0, self.annotations[x_coords_d].num_reads)
                plot.xaxis.bounds = (0, self.annotations[x_coords_d].num_reads)
                plot.xaxis.major_label_text_align = "left"
                plot.xaxis.ticker.min_interval = 1
        if y_coords_d != "full_genome":
            main_layout.heatmap.y_range.start = 0
            main_layout.heatmap.y_range.end = self.annotations[y_coords_d].num_reads
            main_layout.heatmap.y_range.reset_start = 0
            main_layout.heatmap.y_range.reset_end = self.annotations[y_coords_d].num_reads
            for plot in [main_layout.heatmap, main_layout.ratio_x, main_layout.raw_x, main_layout.anno_x,
                        main_layout.heatmap_y_axis]:
                plot.ygrid.minor_grid_line_alpha = plot.ygrid.grid_line_alpha
                plot.ygrid.minor_grid_line_color = plot.ygrid.grid_line_color
                plot.ygrid.grid_line_color = c
                plot.ygrid.minor_grid_line_color = c2
                plot.ygrid.ticker = ticker_border
                plot.ygrid.bounds = (0, self.annotations[y_coords_d].num_reads)
                plot.yaxis.bounds = (0, self.annotations[y_coords_d].num_reads)
                plot.yaxis.major_label_text_align = "right"
                plot.yaxis.ticker.min_interval = 1
        self.chr_sizes.setup_coordinates(main_layout, show_grid_lines, x_coords_d, y_coords_d)

    def setup(self, main_layout):
        self.chr_sizes.setup(main_layout)
        
        if hasattr(self, "info"):
            main_layout.info_div.text = self.info
        opt = [ (str(idx), data[0]) for idx, data in enumerate(self.datasets)]
        main_layout.group_a.options = opt
        main_layout.group_b.options = opt
        main_layout.group_a.value = [ str(idx) for idx, data in enumerate(self.datasets) if data[2] in ["a", "both"] ]
        main_layout.group_b.value = [ str(idx) for idx, data in enumerate(self.datasets) if data[2] in ["b", "both"] ]
        opt = [ (str(idx), data[0]) for idx, data in enumerate(self.normalizations)]
        main_layout.norm_x.options = opt
        main_layout.norm_y.options = opt
        main_layout.norm_x.value = [ str(idx) for idx, data in enumerate(
                                                                self.normalizations) if data[2] in ["col", "both"] ]
        main_layout.norm_y.value = [ str(idx) for idx, data in enumerate(
                                                                self.normalizations) if data[2] in ["row", "both"] ]

        opt = [(x, x) for x in self.annotations.keys()]
        main_layout.displayed_annos.options = opt
        main_layout.filtered_annos_x.options = opt
        main_layout.filtered_annos_y.options = opt
        main_layout.displayed_annos.value = [x for x in self.annotations.keys()]

        possible_coords = [("Genomic loci", "full_genome")]
        for anno_names in self.annotations.keys():
            possible_coords.append((anno_names, anno_names))
        main_layout.x_coords_update(possible_coords)
        main_layout.y_coords_update(possible_coords)

