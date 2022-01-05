from bokeh.layouts import grid, row, column
from bokeh.plotting import figure, curdoc
from bokeh.models.tools import ToolbarBox, ProxyToolbar
from bokeh.models import ColumnDataSource, Dropdown, Button, RangeSlider, Slider, FileInput, TextInput, MultiChoice
import math
from datetime import datetime
from tornado import gen
from bokeh.document import without_document_lock
from bokeh.models import Panel, Tabs
from bokeh.models import Range1d
from meta_data import *
import os
from heatmap_as_r_tree import *
from bokeh.palettes import Viridis256

SETTINGS_WIDTH = 200
DEFAULT_SIZE = 50
ANNOTATION_PLOT_NAME = "Annotation"
RATIO_PLOT_NAME = "Ratio"
RAW_PLOT_NAME = "Raw"

class FigureMaker:
    _show_hide = {}
    _hidable_plots = []
    _unhide_button = None

    def __init__(self):
        self.args = {}
        self.x_axis_visible = False
        self.y_axis_visible = False
        self.toolbar_list = None
        self._hide_on = []
        self.x_axis_label_orientation = None
        self.y_axis_label = ""
        self.x_axis_label = ""
        self._range1d = False
        self.no_border_h = False
        self.no_border_v = False

    def get(self):
        ret = figure(**self.args)
        ret.x(x=0, y=0, line_color=None)
        ret.xaxis.visible = self.x_axis_visible
        ret.yaxis.visible = self.y_axis_visible
        ret.yaxis.axis_label  = self.y_axis_label
        ret.xaxis.axis_label  = self.x_axis_label
        if not self.toolbar_list is None:
            self.toolbar_list.append(ret.toolbar)
            ret.toolbar_location = None
        if len(self._hide_on) > 0:
            FigureMaker._hidable_plots.append( (ret, self._hide_on) )
        if not self.x_axis_label_orientation is None:
            ret.xaxis.major_label_orientation = self.x_axis_label_orientation
        if self._range1d:
            ret.x_range = Range1d()
            ret.y_range = Range1d()
        ret.min_border_left = 0
        ret.min_border_bottom = 0
        if self.no_border_h:
            ret.min_border_right = 0
        if self.no_border_v:
            ret.min_border_top = 0
        return ret

    def range1d(self):
        self._range1d = True
        return self

    def w(self, w):
        self.args["width"] = w
        return self

    def h(self, h):
        self.args["height"] = h
        return self

    def link_y(self, other):
        self.args["y_range"] = other.y_range
        self.args["sizing_mode"] = "stretch_height"
        self.args["height"] = 10
        self.no_border_v = True
        return self

    def link_x(self, other):
        self.args["x_range"] = other.x_range
        self.args["sizing_mode"] = "stretch_width"
        self.args["width"] = 10
        self.no_border_h = True
        return self

    def stretch(self):
        self.args["sizing_mode"] = "stretch_both"
        self.args["height"] = 10
        self.args["width"] = 10
        self.no_border_h = True
        self.no_border_v = True
        return self

    def _axis_of(self, other):
        self.hide_on("axis")
        for plot, _hide_on in FigureMaker._hidable_plots:
            if plot == other:
                for key in _hide_on:
                    self.hide_on(key)

    def x_axis_of(self, other, label=""):
        self._axis_of(other)

        self.x_axis_visible = True
        self.args["x_range"] = other.x_range
        self.args["frame_height"] = 1
        if other.sizing_mode in ["stretch_both", "stretch_width"]:
            self.args["sizing_mode"] = "stretch_width"
            self.w(10)
        else:
            self.w(other.width)
            self.args["sizing_mode"] = "fixed"
        self.args["align"] = "start"
        self.x_axis_label_orientation = math.pi/4
        self.x_axis_label = label
        self.no_border_v = True
        return self

    def y_axis_of(self, other, label=""):
        self._axis_of(other)

        self.y_axis_visible = True
        self.args["y_range"] = other.y_range
        self.args["frame_width"] = 1
        if other.sizing_mode in ["stretch_both", "stretch_height"]:
            self.args["sizing_mode"] = "stretch_height"
            self.h(10)
        else:
            self.h(other.height)
            self.args["sizing_mode"] = "fixed"
        self.args["align"] = "end"
        self.y_axis_label = label
        self.no_border_h = True
        return self

    def hide_on(self, key):
        if not key in FigureMaker._show_hide:
            FigureMaker._show_hide[key] = True
        self._hide_on.append(key)
        return self

    def combine_tools(self, toolbar_list):
        self.toolbar_list = toolbar_list
        return self

    @staticmethod
    def get_tools(tools_list, toolbar_location="above", **toolbar_options):
        tools = sum([ toolbar.tools for toolbar in tools_list ], [])
        proxy = ProxyToolbar(toolbars=tools_list, tools=tools, **toolbar_options)
        proxy.logo = None
        return ToolbarBox(toolbar=proxy, toolbar_location=toolbar_location)

    @staticmethod
    def update_visibility():
        for plot, keys in FigureMaker._hidable_plots:
            plot.visible = True
            for key in keys:
                if not FigureMaker._show_hide[key]:
                    plot.visible = False
                    break
        if not FigureMaker._unhide_button is None:
            FigureMaker._unhide_button.visible = not FigureMaker._show_hide["tools"]

    @staticmethod
    def toggle_hide(key):
        FigureMaker._show_hide[key] = not FigureMaker._show_hide[key]
        FigureMaker.update_visibility()

    @staticmethod
    def show_hide_dropdown(*names):
        for _, key in names:
            if key not in FigureMaker._show_hide:
                FigureMaker._show_hide[key] = True
        def make_menu():
            menu = []
            for name, key in names:
                menu.append((("☑ " if FigureMaker._show_hide[key] or key == "tools" else "☐ ") + name, key))
            return menu
        ret = Dropdown(label="Show/Hide", menu=make_menu(), width=SETTINGS_WIDTH)
        ret.sizing_mode = "fixed"
        def event(e):
            FigureMaker.toggle_hide(e.item)
            ret.menu = make_menu()
        ret.on_click(event)
        return ret

    @staticmethod
    def reshow_settings():
        FigureMaker._unhide_button = Button(label="<", width=40, height=40)
        FigureMaker._unhide_button.sizing_mode = "fixed"
        FigureMaker._unhide_button.visible = False
        def event(e):
            FigureMaker.toggle_hide("tools")
        FigureMaker._unhide_button.on_click(event)
        return FigureMaker._unhide_button




class MainLayout:
    def dropdown_select(self, title, event, *options):
        d = {}
        for _, key in options:
            d[key] = False
        d[options[0][1]] = True
        def make_menu():
            menu = []
            for name, key in options:
                menu.append((("☑ " if d[key] else "☐ ") + name, key))
            return menu
        ret = Dropdown(label=title, menu=make_menu(), width=SETTINGS_WIDTH)
        ret.sizing_mode = "fixed"
        def _event(e):
            for _, key in options:
                d[key] = False
            d[e.item] = True
            event(e.item)
            ret.menu = make_menu()
            self.trigger_render()
        ret.on_click(_event)
        return ret

    def __init__(self):
        self.meta = None
        self.do_render = False
        self.force_render = True
        self.curdoc = curdoc()
        self.last_drawing_area = (0,0,0,0)
        self.idx = None

        global SETTINGS_WIDTH
        tollbars = []
        self.heatmap = FigureMaker().range1d().stretch().combine_tools(tollbars).get()

        d = {"b": [], "l": [], "t": [], "r": [], "c": []}
        self.heatmap_data=ColumnDataSource(data=d)
        self.heatmap.quad(left="l", bottom="b", right="r", top="t", fill_color="c", line_color=None,
              source=self.heatmap_data, level="image")


        self.heatmap_x_axis = FigureMaker().x_axis_of(self.heatmap, "DNA").combine_tools(tollbars).get()
        self.heatmap_y_axis = FigureMaker().y_axis_of(self.heatmap, "RNA").combine_tools(tollbars).get()

        self.ratio_x = FigureMaker().w(DEFAULT_SIZE).link_y(self.heatmap).hide_on("ratio").combine_tools(tollbars).get()
        self.ratio_x_axis = FigureMaker().x_axis_of(self.ratio_x).combine_tools(tollbars).get()

        self.ratio_y = FigureMaker().h(DEFAULT_SIZE).link_x(self.heatmap).hide_on("ratio").combine_tools(tollbars).get()
        self.ratio_y_axis = FigureMaker().y_axis_of(self.ratio_y).combine_tools(tollbars).get()

        self.raw_x = FigureMaker().w(DEFAULT_SIZE).link_y(self.heatmap).hide_on("raw").combine_tools(tollbars).get()
        self.raw_x_axis = FigureMaker().x_axis_of(self.raw_x).combine_tools(tollbars).get()

        self.raw_y = FigureMaker().h(DEFAULT_SIZE).link_x(self.heatmap).hide_on("raw").combine_tools(tollbars).get()
        self.raw_y_axis = FigureMaker().y_axis_of(self.raw_y).combine_tools(tollbars).get()

        self.anno_x = FigureMaker().w(DEFAULT_SIZE).link_y(self.heatmap).hide_on("annotation").combine_tools(tollbars).get()
        self.anno_x_axis = FigureMaker().x_axis_of(self.anno_x).combine_tools(tollbars).get()

        self.anno_y = FigureMaker().h(DEFAULT_SIZE).link_x(self.heatmap).hide_on("annotation").combine_tools(tollbars).get()
        self.anno_y_axis = FigureMaker().y_axis_of(self.anno_y).combine_tools(tollbars).get()

        tool_bar = FigureMaker.get_tools(tollbars)
        SETTINGS_WIDTH = tool_bar.width
        show_hide = FigureMaker.show_hide_dropdown(("Axes", "axis"), (RATIO_PLOT_NAME, "ratio"), (RAW_PLOT_NAME, "raw"),
                                                   (ANNOTATION_PLOT_NAME, "annotation"), ("Tools", "tools"))

        self.in_group_d = "sum"
        def in_group_event(e):
            self.in_group_d = e
            self.trigger_render()
        self.in_group = self.dropdown_select("In Group", in_group_event, ("Sum", "sum"), ("Minimium", "min"), 
                                                                         ("Difference", "dif"))

        self.betw_group_d = "sum"
        def betw_group_event(e):
            self.betw_group_d = e
            self.trigger_render()
        self.betw_group = self.dropdown_select("Between Group", betw_group_event,
                        ("Sum", "sum"), ("Show First Group", "1st"), ("Show Second Group", "2nd"), ("Substract", "sub"),
                        ("Difference", "dif"),("Minimum", "min"))

        self.symmetrie_d = "all"
        def symmetrie_event(e):
            self.symmetrie_d = e
            self.trigger_render()
        self.symmetrie = self.dropdown_select("Symmetry", symmetrie_event,
                        ("Show All", "all"), ("Only Show Symmetric", "sym"), ("Only Show Asymmetric", "asym"))

        self.normalization_d = "max_bin_visible"
        def normalization_event(e):
            self.normalization_d = e
            self.trigger_render()
        self.normalization = self.dropdown_select("Normalize by", normalization_event,
                        ("Largest Rendered Bin", "max_bin_visible"),
                        ("Number of Reads", "num_reads"), ("Column", "column"), ("Coverage", "tracks"))

        self.mapq_slider = RangeSlider(width=SETTINGS_WIDTH, start=0, end=255, value=(0,255), step=1,
                                  title="Mapping Quality Bounds")
        self.mapq_slider.sizing_mode = "fixed"
        self.mapq_slider.on_change("value_throttled", lambda x,y,z: self.trigger_render())

        self.interactions_bounds_slider = Slider(width=SETTINGS_WIDTH, start=1, end=1000, value=1, step=1,
                                  title="Color Scale Begin")
        self.interactions_bounds_slider.sizing_mode = "fixed"
        self.interactions_bounds_slider.on_change("value_throttled", lambda x,y,z: self.trigger_render())

        self.interactions_slider = Slider(width=SETTINGS_WIDTH, start=1, end=1.1, value=1.06, step=0.001,
                                  title="Color Scale Log Base", format="0[.]000")
        self.interactions_slider.sizing_mode = "fixed"
        self.interactions_slider.on_change("value_throttled", lambda x,y,z: self.trigger_render())

        self.update_frequency_slider = Slider(width=SETTINGS_WIDTH, start=0.1, end=3, value=0.5, step=0.1,
                                  title="Update Frequency [seconds]", format="0[.]000")
        self.update_frequency_slider.sizing_mode = "fixed"

        self.redraw_slider = Slider(width=SETTINGS_WIDTH, start=0, end=100, value=50, step=1,
                                  title="Redraw if [%] of shown area changed")
        self.redraw_slider.sizing_mode = "fixed"

        self.anno_size_slider = Slider(width=SETTINGS_WIDTH, start=10, end=500, value=DEFAULT_SIZE, step=1,
                                  title=ANNOTATION_PLOT_NAME + " Plot Size")
        self.anno_size_slider.sizing_mode = "fixed"
        def anno_size_slider_event(attr, old, new):
            self.anno_x.width = self.anno_size_slider.value
            self.anno_x_axis.width = self.anno_size_slider.value
            self.anno_y.height = self.anno_size_slider.value
            self.anno_y_axis.height = self.anno_size_slider.value
        self.anno_size_slider.on_change("value_throttled",anno_size_slider_event)
        
        self.ratio_size_slider = Slider(width=SETTINGS_WIDTH, start=10, end=500, value=DEFAULT_SIZE, step=1,
                                  title=RATIO_PLOT_NAME + " Plot Size")
        self.ratio_size_slider.sizing_mode = "fixed"
        def ratio_size_slider_event(attr, old, new):
            self.ratio_x.width = self.ratio_size_slider.value
            self.ratio_x_axis.width = self.ratio_size_slider.value
            self.ratio_y.height = self.ratio_size_slider.value
            self.ratio_y_axis.height = self.ratio_size_slider.value
        self.ratio_size_slider.on_change("value_throttled",ratio_size_slider_event)
        
        self.raw_size_slider = Slider(width=SETTINGS_WIDTH, start=10, end=500, value=DEFAULT_SIZE, step=1,
                                  title=RAW_PLOT_NAME + " Plot Size")
        self.raw_size_slider.sizing_mode = "fixed"
        def raw_size_slider_event(attr, old, new):
            self.raw_x.width = self.raw_size_slider.value
            self.raw_x_axis.width = self.raw_size_slider.value
            self.raw_y.height = self.raw_size_slider.value
            self.raw_y_axis.height = self.raw_size_slider.value
        self.raw_size_slider.on_change("value_throttled",raw_size_slider_event)


        self.num_bins = Slider(width=SETTINGS_WIDTH, start=1000, end=100000, value=20000, step=1000,
                                  title="Number of Bins")
        self.num_bins.sizing_mode = "fixed"

        self.meta_file = TextInput(value="heatmap_server/out/")
        self.meta_file.on_change("value", lambda x,y,z: self.setup())

        self.group_a = MultiChoice(value=[], options=[],
                                    placeholder="Group A")
        self.group_a.on_change("value", lambda x,y,z: self.trigger_render())


        _settings = Tabs(
            tabs=[
                Panel(child=column([tool_bar, self.meta_file, show_hide, self.symmetrie]), 
                        title="General"),
                Panel(child=column([self.normalization, self.mapq_slider, self.interactions_bounds_slider,
                                    self.interactions_slider]),
                        title="Normalization"),
                Panel(child=column([self.in_group, self.betw_group, self.group_a]),
                        title="Replicates"),
                Panel(child=column([self.num_bins, self.update_frequency_slider, self.redraw_slider,
                                    self.anno_size_slider, self.raw_size_slider, self.ratio_size_slider]),
                        title="GUI"),
            ],
            sizing_mode="stretch_height"
        )

        FigureMaker._hidable_plots.append((_settings, ["tools"]))
        settings = row([_settings, FigureMaker.reshow_settings()], sizing_mode="stretch_height")

        grid_layout = [
[self.heatmap_y_axis, self.anno_x,   self.raw_x,      self.ratio_x,      None,              self.heatmap,   settings],
[None,              self.anno_x_axis, self.raw_x_axis, self.ratio_x_axis, None,              None,               None],
[None,              None,             None,            None,              self.ratio_y_axis, self.ratio_y,       None],
[None,              None,             None,            None,              self.raw_y_axis,   self.raw_y,         None],
[None,              None,             None,            None,              self.anno_y_axis,  self.anno_y,        None],
[None,              None,             None,            None,              None,            self.heatmap_x_axis, None],
        ]

        self.root = grid(grid_layout, sizing_mode="stretch_both")

    # overlap of the given areas relative to the larger area
    @staticmethod
    def area_overlap(a, b):
        a_xs, a_ys, a_xe, a_ye = a
        a_a = (a_xe - a_xs) * (a_ye - a_ys)
        b_xs, b_ys, b_xe, b_ye = b
        b_a = (b_xe - b_xs) * (b_ye - b_ys)

        # get interseciton
        i_xe = min(a_xe, b_xe)
        i_ye = min(a_ye, b_ye)
        i_xs = max(a_xs, b_xs)
        i_ys = max(a_ys, b_ys)
        i_a = (i_xe - i_xs) * (i_ye - i_ys)

        return i_a / max(b_a, a_a)

    def bin_cols_or_rows(self, area, h_bin, base_idx=0):
        h_bin = max(1, h_bin)
        ret = []
        x_chrs = [idx for idx, (start, size) in enumerate(zip(self.meta.chr_sizes.chr_starts,
                                                              self.meta.chr_sizes.chr_sizes_l))
                        if start <= area[base_idx+2] and start + size >= area[base_idx] and size >= h_bin]
        for x_chr in x_chrs:
            x = max(int(area[base_idx]), self.meta.chr_sizes.chr_starts[x_chr])
            x_end = self.meta.chr_sizes.chr_starts[x_chr] + self.meta.chr_sizes.chr_sizes_l[x_chr]
            while x <= min(area[base_idx+2], x_end):
                ret.append((x, min(h_bin, x_end - x)))
                x += h_bin
        return ret

    def bin_cols(self, area, h_bin):
        return self.bin_cols_or_rows(area, h_bin, 0)

    def bin_rows(self, area, h_bin):
        return self.bin_cols_or_rows(area, h_bin, 1)

    def bin_coords(self, area, h_bin):
        h_bin = max(1, h_bin)
        ret = []
        a = self.bin_cols(area, h_bin)
        b = self.bin_rows(area, h_bin)
        for x, w in a:
            for y, h in b:
                ret.append((x, y, w, h))
        return ret, a, b


    def make_bins(self, bin_coords):
        bins = []
        for idx, _ in enumerate(self.meta.datasets):
            bins.append([])
            for x, y, w, h in bin_coords:
                bins[-1].append(self.idx.count(idx, y, y+h, x, x+w, *self.mapq_slider.value))
        return bins

    def col_norm(self, cols):
        return self.flatten_bins(self.make_bins([(x, 0, w, self.meta.chr_sizes.chr_start_pos["end"]) for x, w in cols]))

    def read_norm(self, idx):
        n = []
        for dataset in self.meta.datasets:
            if dataset[2] == (idx == 0):
                n.append(dataset[3])
        if self.in_group_d == "min":
            n = min(n)
        elif self.in_group_d == "sum":
            n = sum(n)
        elif self.in_group_d == "dif":
            n = sum(abs(x-y) for x in n for y in n)
        else:
            raise RuntimeError("Unknown in group value")
        return n

    def norm_bins(self, bins_l, bin_coords, cols, rows):
        ret = []
        for idx, bins in enumerate(bins_l):
            if self.normalization_d == "max_bin_visible":
                n = max(bins + [1])
                ret.append([x/n for x in bins])
            elif self.normalization_d == "num_reads":
                n = self.read_norm(idx)
                ret.append([x/n for x in bins])
            elif self.normalization_d == "column":
                ns = self.col_norm(cols)
                ret.append([x/max(ns[idx][idx_2//len(rows)],1) for idx_2, x in enumerate(bins)])
            elif self.normalization_d == "tracks":
                raise RuntimeError("unimplemented normalization value")
            else:
                raise RuntimeError("Unknown normalization value")
        return ret

    def flatten_bins(self, bins):
        ret = [[], []]
        for idx, _ in enumerate(bins[0]):
            a = []
            b = []
            for idx_2 in range(len(bins)):
                if str(idx_2) in self.group_a.value:
                    a.append(bins[idx_2][idx])
                else:
                    b.append(bins[idx_2][idx])
            if self.in_group_d == "min":
                aa = min(a + [0])
                bb = min(b + [0])
            elif self.in_group_d == "sum":
                aa = sum(a)
                bb = sum(b)
            elif self.in_group_d == "dif":
                aa = sum(abs(x-y) for x in a for y in a)
                bb = sum(abs(x-y) for x in b for y in b)
            else:
                raise RuntimeError("Unknown in group value")
            ret[0].append(aa)
            ret[1].append(bb)
        return ret

    def color_bins(self, bins):
        ret = []
        for x, y in zip(*bins):
            if self.betw_group_d == "1st":
                ret.append(Viridis256[int(x*255)])
            elif self.betw_group_d == "2nd":
                ret.append(Viridis256[int(y*255)])
            elif self.betw_group_d == "sub":
                ret.append(Viridis256[int( ((x-y)/2+0.5) * 255)])
            elif self.betw_group_d == "min":
                ret.append(Viridis256[int(min(x,y)*255)])
            elif self.betw_group_d == "dif":
                ret.append(Viridis256[int(abs(x-y)*255)])
            elif self.betw_group_d == "sum":
                ret.append(Viridis256[min(int((x+y)*255/2), 255)])
            else:
                raise RuntimeError("Unknown between group value")
        return ret

    def purge(self, bins, bin_coords, background):
        ret1 = []
        ret2 = []
        for x, y in zip(bins, bin_coords):
            if x != background:
                ret1.append(x)
                ret2.append(y)
        return ret1, ret2

    def bin_symmentry(self, bins, bin_coords, bin_cols, bin_rows):
        if self.symmetrie_d == "all":
            return bins
        elif self.symmetrie_d == "sym" or self.symmetrie_d == "asym":
            bins_2 = self.make_bins([(y, x, h, w) for x, y, w, h in bin_coords])
            flat = self.flatten_bins(bins_2)
            norms = self.norm_bins(flat, bin_coords, bin_rows, bin_cols)
            if self.symmetrie_d == "sym":
                return [[min(a, b) for a,b in zip(bin, norm)] for bin, norm in zip(bins, norms)]
            else:
                return [[max(a-b, 0) for a,b in zip(bin, norm)] for bin, norm in zip(bins, norms)]
        else:
            raise RuntimeError("Unknown symmetry value")

    def render(self, area):
        if self.meta is None or self.idx is None:
            return
        area_bin = (area[2] - area[0]) * (area[3] - area[1]) / self.num_bins.value
        def power_of_ten(x):
            n = 0
            while True:
                for i in [1, 1.25, 2.5, 5]:
                    if i*10**n >= x:
                        return i*10**n
                n += 1
        h_bin = power_of_ten(math.sqrt(area_bin))
        bin_coords, bin_cols, bin_rows = self.bin_coords(area, h_bin)
        bins = self.make_bins(bin_coords)
        flat = self.flatten_bins(bins)
        norm = self.norm_bins(flat, bin_coords, bin_cols, bin_rows)
        sym = self.bin_symmentry(norm, bin_coords, bin_cols, bin_rows)
        c = self.color_bins(sym)
        self.heatmap.background_fill_color = Viridis256[255//2] if self.betw_group_d == "sub" else Viridis256[0]
        purged, purged_coords = self.purge(c, bin_coords, self.heatmap.background_fill_color)

        d = {
             "b": [x[1] for x in purged_coords],
             "l": [x[0] for x in purged_coords],
             "t": [x[1] + x[3] for x in purged_coords],
             "r": [x[0] + x[2] for x in purged_coords],
             "c": purged
            }
        self.heatmap_data.data = d


    def setup(self):
        if os.path.exists(self.meta_file.value + ".meta"):
            self.meta = MetaData.load(self.meta_file.value + ".meta")
            self.meta.setup(self)
            if os.path.exists(self.meta_file.value + ".db.idx") and os.path.exists(self.meta_file.value + ".db.dat"):
                self.idx = Tree(self.meta_file.value + ".db")
                self.trigger_render()

    def trigger_render(self):
        self.force_render = True

    def render_callback(self):
        if self.do_render:
            if not None in (self.heatmap.x_range.start, self.heatmap.x_range.end, self.heatmap.y_range.start, self.heatmap.y_range.end):
                curr_area = (self.heatmap.x_range.start, self.heatmap.y_range.start, 
                                self.heatmap.x_range.end, self.heatmap.y_range.end)
                overlap = MainLayout.area_overlap(self.last_drawing_area, curr_area)
                min_change = self.redraw_slider.value/100
                #print(overlap)
                if 1-overlap >= min_change or self.force_render:
                    self.force_render = False
                    w = curr_area[2] - curr_area[0]
                    h = curr_area[3] - curr_area[1]
                    new_area = (curr_area[0] - w*min_change, curr_area[1] - h*min_change,
                                curr_area[2] + w*min_change, curr_area[3] + h*min_change)
                    self.render(new_area)
                    self.last_drawing_area = curr_area

            self.curdoc.add_timeout_callback(lambda: self.render_callback(), self.update_frequency_slider.value*1000)

    def set_root(self):
        self.curdoc.clear()
        self.curdoc.add_root(self.root)
        self.do_render = True
        self.force_render = True
        self.render_callback()
