from libSmoother import Quarry

def write_header(out_file, smoother_version):
    out_file.write("##Smoother " + smoother_version +"\n")
    out_file.write("##LibSps Version: " + Quarry.get_libSps_version() + "\n")
    out_file.write("##LibCm Version: " + Quarry.get_libCm_version() + "\n")


def export_tsv(session, smoother_version):
    if "Heatmap" in session.get_value(["settings", "export", "selection"]):
        with open(session.get_value(["settings", "export", "prefix"]) + ".heatmap.tsv", "w") as out_file:
            write_header(out_file, smoother_version)
            out_file.write("#chr_x\tstart_x\tend_x\tchr_y\tstart_y\tend_y\tscore\n")
            for tup in session.get_heatmap_export():
                out_file.write("\t".join([str(x) for x in tup]) + "\n")

    for x_axis, key, suff in [(True, "Column Coverage", "x"), (False, "Row Coverage", "y")]:
        if key in session.get_value(["settings", "export", "selection"]):
            with open(session.get_value(["settings", "export", "prefix"]) + ".track." + suff + ".tsv", "w") as out_file:
                write_header(out_file, smoother_version)
                out_file.write("#chr_x\tstart_x\tend_x")
                for track in session.get_track_export_names(x_axis):
                    out_file.write("\t" + track)
                out_file.write("\n")

                for tup in session.get_track_export(x_axis):
                    out_file.write("\t".join(["\t".join([str(y) for y in x]) if isinstance(x, list) else str(x) for x in tup]) + "\n")

if False:
    """
    if not self.do_export is None and False:
        if "Data" in self.export_type:
            if "Heatmap" in self.settings["export"]["selection"]:
                with open(self.settings["export"]["prefix"] + ".heatmap.bed", "w") as out_file:
                    out_file.write("##Smoother Version:" + self.smoother_version +"\n##LibSps Version: " + bin.libSps.VERSION + "\n")
                    out_file.write("##Bin width:" + str(h_bin* self.meta.dividend) + " Bin height:" +
                                                    str(w_bin* self.meta.dividend) + "\n")
                    out_file.write("#chr_x\tpos_x\tchr_y\tpos_y\tscore\tannotation_x\tannotation_y\n")
                    for c, (x, y, w, h), (x_chr_, x_2_, y_chr_, y_2_) in zip(
                                self.color_bins_a(sym), bin_coords, bin_coords_2):
                        out_file.write("\t".join([x_chr_, str(int(x_2_) * self.meta.dividend), 
                                                y_chr_, str(int(y_2_) * self.meta.dividend), 
                                                str(c), 
                                                self.make_anno_str(x, x+w), 
                                                self.make_anno_str(y, y+h)]) + "\n")
            if "Column Sum" in self.settings["export"]["selection"]:
                with open(self.settings["export"]["prefix"] + ".columns.bed", "w") as out_file:
                    for c, x_chr_, x_2_, x_ in zip(raw_y_ratio, y_chr, y_pos1, y_pos):
                        if not x_ is float('NaN'):
                            out_file.write("\t".join([x_chr_, str(int(x_2_) * self.meta.dividend), str(c)]) + "\n")
            if "Row Sum" in self.settings["export"]["selection"]:
                with open(self.settings["export"]["prefix"] + ".rows.bed", "w") as out_file:
                    for c, x_chr_, x_2_, x_ in zip(raw_x_ratio, x_chr, x_pos1, x_pos):
                        if not x_ is float('NaN'):
                            out_file.write("\t".join([x_chr_, str(int(x_2_) * self.meta.dividend), str(c)]) + "\n")
        if "Png" in self.export_type:
            export_png(self.heatmap, filename=self.settings["export"]["prefix"] + ".heatmap.png")
        if "Svg" in self.export_type:
            bckup = self.heatmap.output_backend
            self.heatmap.output_backend = "svg"
            export_svg(self.heatmap, filename=self.settings["export"]["prefix"] + ".heatmap.svg")
            self.heatmap.output_backend = bckup
    """