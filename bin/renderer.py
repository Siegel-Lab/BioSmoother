from bin.render_step_logger import Logger

class Renderer:
    def __init__(self):
        self.idx = None
        self.idx_norm = None
        self.render_logger = Logger()
        self.smoother_version = "?"
        self.in_group_d = "sum"
        self.betw_group_d = "sum"
        self.symmetrie_d = "all"
        self.normalization_d = "max_bin_visible"
        self.ddd_d = "no"
        self.square_bins_d = "view"
        self.power_ten_bin_d = "p10"
        self.color_d = "Viridis256"
        self.multi_mapping_d = "enclosed"
        self.stretch_d = "stretch_both"
        self.mapq_min_d = 0
        self.mapq_max_d = 255
        self.interactions_min_d = 0
        self.color_range_start_d = 0
        self.color_range_end_d = 1
        self.interactions_slider_d = 10
        self.update_frequency_slider_d = 0.5
        self.redraw_slider_d = 90
        self.add_area_slider_d = 20
        self.diag_dist_slider_d = 0
        self.anno_size_slide_d = 50
        self.ratio_size_slider_d = 50
        self.raw_size_slider_d = 50
        self.num_bins_d = 50 # in thousands
        self.radical_seq_accept_d = 0.05
        self.meta_file_d = "smoother_out/"
        self.group_a_d = None
        self.group_b_d = None
        self.displayed_annos_d = None
        self.filtered_annos_x_d = None
        self.filtered_annos_y_d = None
        self.min_bin_size_d = 9*2 # @todo convert to actual size
        self.norm_x_d = None
        self.norm_y_d = None
        self.x_coords_d = None
        self.y_coords_d = None
        self.chrom_x_d = None
        self.chrom_y_d = None
        self.multiple_anno_per_bin_d = "combine"
        self.do_export = None
        self.export_file_d = "export"
        self.export_sele_d = ["heatmap"]
        self.show_hide_on = {"grid_lines": False, "contig_borders": True, "indent_line": False,
                             "ratio": False, "raw": True, "annotation": True, "axis": True, "tools": True}
        self.overlay_dataset_id_d = -1

    def setup(self):
        self.group_a_d = []
        self.group_b_d = []
        self.displayed_annos_d = []
        self.filtered_annos_x_d = []
        self.filtered_annos_y_d = []
        self.norm_x_d = []
        self.norm_y_d = []
        #self.x_coords_d = []
        #self.y_coords_d = []
        self.chrom_x_d = []
        self.chrom_y_d = []
        #self.do_export = []