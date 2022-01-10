from bokeh.layouts import grid, row, column
from bokeh.plotting import figure, curdoc
from bokeh.models.tools import ToolbarBox, ProxyToolbar
from bokeh.models import ColumnDataSource, Dropdown, Button, RangeSlider, Slider, FileInput, TextInput, MultiChoice, FuncTickFormatter, Div
import math
from datetime import datetime
from tornado import gen
from bokeh.document import without_document_lock
from bokeh.models import Panel, Tabs
from bokeh.models import Range1d
from meta_data import *
import os
from heatmap_as_r_tree import *
from bokeh.palettes import Viridis256, Category10

SETTINGS_WIDTH = 200
DEFAULT_SIZE = 50
ANNOTATION_PLOT_NAME = "Annotation"
RATIO_PLOT_NAME = "Ratio"
RAW_PLOT_NAME = "Raw"

DIV_MARGIN = (5, 5, 0, 5)

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
        ret.xaxis.axis_label_text_font_size = "10px"
        ret.yaxis.axis_label_text_font_size = "10px"
        ret.xaxis.axis_label_standoff = 0
        ret.yaxis.axis_label_standoff = 0
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
        self.x_axis_label_orientation = math.pi/2
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

    def categorical_x(self):
        self.args["x_range"] = []
        return self

    def categorical_y(self):
        self.args["y_range"] = []
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
        self.curr_area_size = 1
        self.idx = None
        self.idx_norm = None

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
        self.ratio_x_axis.xaxis.axis_label = "Ratio"

        self.ratio_y = FigureMaker().h(DEFAULT_SIZE).link_x(self.heatmap).hide_on("ratio").combine_tools(tollbars).get()
        self.ratio_y_axis = FigureMaker().y_axis_of(self.ratio_y).combine_tools(tollbars).get()
        self.ratio_y_axis.yaxis.axis_label = "Ratio"

        self.raw_x = FigureMaker().w(DEFAULT_SIZE).link_y(self.heatmap).hide_on("raw").combine_tools(tollbars).get()
        self.raw_x_axis = FigureMaker().x_axis_of(self.raw_x).combine_tools(tollbars).get()
        self.raw_x_axis.xaxis.axis_label = "Cov"


        self.raw_y = FigureMaker().h(DEFAULT_SIZE).link_x(self.heatmap).hide_on("raw").combine_tools(tollbars).get()
        self.raw_y_axis = FigureMaker().y_axis_of(self.raw_y).combine_tools(tollbars).get()
        self.raw_y_axis.yaxis.axis_label = "Cov"
        
        d_x = {
            "pos": [],
            "norm": [],
            "heat": [],
            "ratio": [],
        }
        d_y = {
            "pos": [],
            "norm": [],
            "heat": [],
            "ratio": [],
        }
        self.raw_data_x=ColumnDataSource(data=d_x)
        self.raw_data_y=ColumnDataSource(data=d_y)
        self.raw_x.line(x="norm", y="pos", source=self.raw_data_x, line_color="blue") # , level="image"
        self.raw_y.line(x="pos", y="norm", source=self.raw_data_y, line_color="orange") # , level="image"
        self.raw_x.line(x="heat", y="pos", source=self.raw_data_x, line_color="black") # , level="image"
        self.raw_y.line(x="pos", y="heat", source=self.raw_data_y, line_color="black") # , level="image"
        self.ratio_x.line(x="ratio", y="pos", source=self.raw_data_x, line_color="black") # , level="image"
        self.ratio_y.line(x="pos", y="ratio", source=self.raw_data_y, line_color="black") # , level="image"

        self.anno_x = FigureMaker().w(DEFAULT_SIZE).link_y(self.heatmap).hide_on("annotation").combine_tools(tollbars).categorical_x().get()
        self.anno_x_axis = FigureMaker().x_axis_of(self.anno_x).combine_tools(tollbars).get()
        self.anno_x_axis.xaxis.axis_label = "Anno"

        self.anno_y = FigureMaker().h(DEFAULT_SIZE).link_x(self.heatmap).hide_on("annotation").combine_tools(tollbars).categorical_y().get()
        self.anno_y_axis = FigureMaker().y_axis_of(self.anno_y).combine_tools(tollbars).get()
        self.anno_y_axis.yaxis.axis_label = "Anno"
        
        d = {"x": [], "s": [], "e": [], "c": []}
        self.anno_x_data=ColumnDataSource(data=d)
        self.anno_x.vbar(x="x", top="e", bottom="s", width=0.9, fill_color="c", line_color=None,
              source=self.anno_x_data)
        self.anno_y_data=ColumnDataSource(data=d)
        self.anno_y.hbar(y="x", right="e", left="s", height=0.9, fill_color="c", line_color=None,
              source=self.anno_y_data)

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
                        ("Number of Reads", "num_reads"), ("Column", "column"), 
                        ("Coverage of Normalization Reads (Absolute)", "tracks_abs"),
                        ("Coverage of Normalization Reads (Scaled to Rendered Area)", "tracks_rel"))

        self.mapq_slider = RangeSlider(width=SETTINGS_WIDTH, start=0, end=255, value=(0,255), step=1,
                                  title="Mapping Quality Bounds")
        self.mapq_slider.sizing_mode = "fixed"
        self.mapq_slider.on_change("value_throttled", lambda x,y,z: self.trigger_render())

        self.interactions_bounds_slider = Slider(width=SETTINGS_WIDTH, start=0, end=100, value=0, step=1,
                                  title="Color Scale Begin")
        self.interactions_bounds_slider.sizing_mode = "fixed"
        self.interactions_bounds_slider.on_change("value_throttled", lambda x,y,z: self.trigger_render())

        self.interactions_slider = Slider(width=SETTINGS_WIDTH, start=-50, end=50, value=10, step=0.1,
                                  title="Color Scale Log Base")#, format="0[.]000")
        self.interactions_slider.sizing_mode = "fixed"
        self.interactions_slider.on_change("value_throttled", lambda x,y,z: self.trigger_render())

        self.update_frequency_slider = Slider(width=SETTINGS_WIDTH, start=0.1, end=3, value=0.5, step=0.1,
                                  title="Update Frequency [seconds]", format="0[.]000")
        self.update_frequency_slider.sizing_mode = "fixed"

        self.redraw_slider = Slider(width=SETTINGS_WIDTH, start=0, end=100, value=90, step=1,
                                  title="Redraw if zoomed in by [%]")
        self.redraw_slider.sizing_mode = "fixed"

        self.add_area_slider = Slider(width=SETTINGS_WIDTH, start=0, end=500, value=100, step=10,
                                  title="Additional Draw Area [%]")
        self.add_area_slider.sizing_mode = "fixed"
        self.add_area_slider.on_change("value_throttled", lambda x,y,z: self.trigger_render())

        self.diag_dist_slider = Slider(width=SETTINGS_WIDTH, start=0, end=1000, value=0, step=1,
                                  title="Minimum Distance from Diagonal")
        self.diag_dist_slider.sizing_mode = "fixed"
        self.diag_dist_slider.on_change("value_throttled", lambda x,y,z: self.trigger_render())

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


        self.num_bins = Slider(width=SETTINGS_WIDTH, start=1000, end=100000, value=30000, step=1000,
                                  title="Number of Bins")
        self.num_bins.sizing_mode = "fixed"
        self.num_bins.on_change("value_throttled", lambda x,y,z: self.trigger_render())

        self.meta_file = TextInput(value="heatmap_server/out/")
        self.meta_file.on_change("value", lambda x,y,z: self.setup())

        self.group_a = MultiChoice(value=[], options=[],
                                    placeholder="Group A")
        self.group_a.on_change("value", lambda x,y,z: self.trigger_render())
        self.group_b = MultiChoice(value=[], options=[],
                                    placeholder="Group B")
        self.group_b.on_change("value", lambda x,y,z: self.trigger_render())

        div_displayed_annos = Div(text="Displayed Annotations:")
        div_displayed_annos.margin = DIV_MARGIN
        self.displayed_annos = MultiChoice(value=[], options=[])
        self.displayed_annos.on_change("value", lambda x,y,z: self.trigger_render())

        power_tick = FuncTickFormatter(code="return \"10^\"+Math.floor(tick)")#Math.pow(10, tick)
        self.min_max_bin_size = RangeSlider(start=0, end=15, value=(0,6), step=1, title="Bin Size Bounds [nt]",
                                            format=power_tick)
        self.min_max_bin_size.on_change("value_throttled", lambda x,y,z: self.trigger_render())

        self.curr_bin_size = Div(text="Current Bin Size: n/a")
        div_group_a = Div(text="Group A:")
        div_group_a.margin = DIV_MARGIN
        div_group_b = Div(text="Group B:")
        div_group_b.margin = DIV_MARGIN

        div_norm_x = Div(text="Normalization Rows:")
        div_norm_x.margin = DIV_MARGIN
        div_norm_y = Div(text="Normalization Columns:")
        div_norm_y.margin = DIV_MARGIN
        self.norm_x = MultiChoice(value=[], options=[])
        self.norm_x.on_change("value", lambda x,y,z: self.trigger_render())
        self.norm_y = MultiChoice(value=[], options=[])
        self.norm_y.on_change("value", lambda x,y,z: self.trigger_render())


        _settings = Tabs(
            tabs=[
                Panel(child=column([tool_bar, self.meta_file, show_hide, self.symmetrie, self.diag_dist_slider,
                                    div_displayed_annos, self.displayed_annos, self.min_max_bin_size,
                                    self.curr_bin_size]), 
                        title="General"),
                Panel(child=column([self.normalization, self.mapq_slider, self.interactions_bounds_slider,
                                    self.interactions_slider, div_norm_x, self.norm_x, div_norm_y, self.norm_y]),
                        title="Normalization"),
                Panel(child=column([self.in_group, self.betw_group, div_group_a, self.group_a, div_group_b, self.group_b]),
                        title="Replicates"),
                Panel(child=column([self.num_bins, self.update_frequency_slider, self.redraw_slider, 
                                    self.add_area_slider,
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

    @staticmethod
    def area_outside(last, curr):
        a_xs, a_ys, a_xe, a_ye = last
        b_xs, b_ys, b_xe, b_ye = curr

        return b_xs < a_xs or b_ys < a_ys or b_xe > a_xe or b_ye > a_ye

    def bin_cols_or_rows(self, area, h_bin, base_idx=0, none_for_chr_border=False):
        h_bin = max(1, h_bin)
        ret = []
        x_chrs = [idx for idx, (start, size) in enumerate(zip(self.meta.chr_sizes.chr_starts,
                                                              self.meta.chr_sizes.chr_sizes_l))
                        if start <= area[base_idx+2] and start + size >= area[base_idx] and size >= h_bin]
        if none_for_chr_border:
            ret.append(None)
        for x_chr in x_chrs:
            x = max(int(area[base_idx]), self.meta.chr_sizes.chr_starts[x_chr])
            x_end = self.meta.chr_sizes.chr_starts[x_chr] + self.meta.chr_sizes.chr_sizes_l[x_chr]
            while x <= min(area[base_idx+2], x_end):
                ret.append((x, min(h_bin, x_end - x)))
                x += h_bin
            if none_for_chr_border:
                ret.append(None)
        return ret

    def bin_cols(self, area, h_bin, none_for_chr_border=False):
        return self.bin_cols_or_rows(area, h_bin, 0, none_for_chr_border)

    def bin_rows(self, area, h_bin, none_for_chr_border=False):
        return self.bin_cols_or_rows(area, h_bin, 1, none_for_chr_border)

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
        min_ = self.interactions_bounds_slider.value
        for idx, _ in enumerate(self.meta.datasets):
            bins.append([])
            for x, y, w, h in bin_coords:
                if abs(x - y) >= self.diag_dist_slider.value:
                    bins[-1].append(
                        max(self.idx.count(idx, y, y+h, x, x+w, *self.mapq_slider.value)-min_, 0))
                else:
                    bins[-1].append(0)
        return bins

    def col_norm(self, cols):
        return self.flatten_bins(self.make_bins([(c[0], 0, c[1], self.meta.chr_sizes.chr_start_pos["end"]) \
                            if not c is None else (-2,-2,1,1) for c in cols]))

    def row_norm(self, rows):
        return self.flatten_bins(self.make_bins([(0, c[0], self.meta.chr_sizes.chr_start_pos["end"], c[1]) \
                            if not c is None else (-2,-2,1,1) for c in rows]))

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

    def norm_num_reads(self, rows):
        return self.flatten_norm([
            [self.idx_norm.count(int(idx), 0, self.meta.chr_sizes.chr_start_pos["end"], *self.mapq_slider.value)
                for idx in (self.norm_x.value if rows else self.norm_y.value)]] )[0]

    def norm_bins(self, bins_l, cols, rows):
        ret = []
        if self.normalization_d in ["tracks_abs", "tracks_rel"]:
            raw_x_norm = self.linear_bins_norm(rows, True)
            raw_y_norm = self.linear_bins_norm(cols, False)
        for idx, bins in enumerate(bins_l):
            if self.normalization_d == "max_bin_visible":
                n = max(bins + [1])
                ret.append([x/n for x in bins])
            elif self.normalization_d == "num_reads":
                n = self.read_norm(idx)
                ret.append([x/n for x in bins])
            elif self.normalization_d == "column":
                ns = self.col_norm(cols)
                ret.append([x/max(ns[idx][idx_2 // len(rows)],1) for idx_2, x in enumerate(bins)])
            elif self.normalization_d in ["tracks_abs", "tracks_rel"]:
                n = self.read_norm(idx)
                def get_norm(i):
                    d = (raw_y_norm[i // len(rows)] * raw_x_norm[i % len(rows)] * n)
                    if d == 0:
                        return 0
                    return (self.norm_num_reads(True) * self.norm_num_reads(False)) / d
                ret.append([x*get_norm(idx_2) for idx_2, x in enumerate(bins)])
                if self.normalization_d == "tracks_rel":
                    _max = max(*ret[-1], 0.001)
                    for i in range(len(ret[-1])):
                        ret[-1][i] = ret[-1][i] / _max
                else:
                    for i in range(len(ret[-1])):
                        ret[-1][i] = min(ret[-1][i], 1)
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
                if str(idx_2) in self.group_b.value:
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

    def flatten_norm(self, bins):
        ret = []
        for x in bins:
            if x is None:
                ret.append(x)
            elif self.in_group_d == "min":
                ret.append(min(x))
            elif self.in_group_d == "sum":
                ret.append(sum(x))
            elif self.in_group_d == "dif":
                ret.append(sum(abs(a-b) for a in x for b in x))
        return ret

    #used function:
    # copy paste into https://www.desmos.com/calculator/auubsajefh
    # y=\frac{\log\left(2^{a}\cdot\left(x\cdot\left(1-\frac{1}{2^{a}}\right)+\frac{1}{2^{a}}\right)\right)}{\log\left(2^{a}\right)}
    def log_scale(self, c):
        if self.interactions_slider.value == 0:
            return c
        a = 2**self.interactions_slider.value
        c = math.log(a*(c*(1-(1/a))+(1/a))) / math.log(a)
        return c

    def color_bins_a(self, bins):
        ret = []
        for x, y in zip(*bins):
            c = 0
            if self.betw_group_d == "1st":
                c = x
            elif self.betw_group_d == "2nd":
                c = y
            elif self.betw_group_d == "sub":
                c = (x - y)
            elif self.betw_group_d == "min":
                c = min(x, y)
            elif self.betw_group_d == "dif":
                c = abs(x - y)
            elif self.betw_group_d == "sum":
                c = (x + y) / 2
            else:
                raise RuntimeError("Unknown between group value")
            ret.append(c)
        return ret
    def color_bins_b(self, bins):
        ret = []
        for c in bins:
            if self.betw_group_d == "sub":
                c = self.log_scale(abs(c)) * (1 if c >= 0 else -1) / 2 + 0.5
                c = max(0, min(255, int(255*c)))
                ret.append(Viridis256[c])
            else:
                ret.append(Viridis256[max(0, min(255, int(255*self.log_scale(c))))])
        return ret

    def color_bins(self, bins):
        return self.color_bins_b(self.color_bins_a(bins))

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
            raw_x_norm = self.linear_bins_norm(bin_cols, True)
            raw_y_norm = self.linear_bins_norm(bin_rows, False)
            norms = self.norm_bins(flat, bin_coords, bin_rows, bin_cols, raw_x_norm, raw_y_norm)
            if self.symmetrie_d == "sym":
                return [[min(a, b) for a,b in zip(bin, norm)] for bin, norm in zip(bins, norms)]
            else:
                return [[max(a-b, 0) for a,b in zip(bin, norm)] for bin, norm in zip(bins, norms)]
        else:
            raise RuntimeError("Unknown symmetry value")

    def annotation_bins(self, bins, coverage_obj):
        return [coverage_obj.count(x[0], x[0] + x[1]) if not x is None else float('NaN') for x in bins]

    def linear_bins_norm(self, bins, rows):
        return self.flatten_norm([
            [self.idx_norm.count(int(idx), x[0], x[0] + x[1], *self.mapq_slider.value)
                for idx in (self.norm_x.value if rows else self.norm_y.value)]
                    if not x is None else [float('NaN')] for x in bins] )

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
        h_bin = min(max(h_bin, 10**self.min_max_bin_size.value[0]), 10**self.min_max_bin_size.value[1])
        bin_coords, bin_cols, bin_rows = self.bin_coords(area, h_bin)
        bins = self.make_bins(bin_coords)
        flat = self.flatten_bins(bins)
        norm = self.norm_bins(flat, bin_cols, bin_rows)
        sym = self.bin_symmentry(norm, bin_coords, bin_cols, bin_rows)
        c = self.color_bins(sym)
        b_col = Viridis256[255//2] if self.betw_group_d == "sub" else Viridis256[0]
        purged, purged_coords = self.purge(c, bin_coords, b_col)


        d_heatmap = {
             "b": [x[1] for x in purged_coords],
             "l": [x[0] for x in purged_coords],
             "t": [x[1] + x[3] for x in purged_coords],
             "r": [x[0] + x[2] for x in purged_coords],
             "c": purged
            }


        raw_bin_rows = self.bin_rows(area, h_bin, True)
        raw_bin_cols = self.bin_cols(area, h_bin, True)

        raw_x_norm = self.linear_bins_norm(raw_bin_rows, True)
        raw_y_norm = self.linear_bins_norm(raw_bin_cols, False)
        raw_x_heat = self.color_bins_a(self.row_norm(raw_bin_rows))
        raw_y_heat = self.color_bins_a(self.col_norm(raw_bin_cols))
        raw_x_ratio = [a/b if not b == 0 else 0 for a, b in zip(raw_x_heat, raw_x_norm)]
        raw_y_ratio = [a/b if not b == 0 else 0 for a, b in zip(raw_y_heat, raw_y_norm)]

        raw_data_x = {
            "pos": [x[0] + x[1]/2 if not x is None else float('NaN') for x in raw_bin_rows],
            "norm": raw_x_norm,
            "heat": raw_x_heat,
            "ratio": raw_x_ratio,
        }
        raw_data_y = {
            "pos": [x[0] + x[1]/2 if not x is None else float('NaN') for x in raw_bin_cols],
            "norm": raw_y_norm,
            "heat": raw_y_heat,
            "ratio": raw_y_ratio,
        }

        d_anno_x = {
            "x": [],
            "s": [],
            "e": [],
            "c": []
        }
        for idx, anno in enumerate(self.displayed_annos.value):
            for (s, e), x in zip(bin_rows, self.annotation_bins(bin_rows, self.meta.annotations[anno])):
                if x > 0:
                    d_anno_x["x"].append(anno)
                    d_anno_x["s"].append(s)
                    d_anno_x["e"].append(s + e)
                    d_anno_x["c"].append(Category10[10][idx % 10])
        d_anno_y = {
            "x": [],
            "s": [],
            "e": [],
            "c": []
        }
        for idx, anno in enumerate(self.displayed_annos.value):
            for (s, e), x in zip(bin_cols, self.annotation_bins(bin_cols, self.meta.annotations[anno])):
                if x > 0:
                    d_anno_y["x"].append(anno)
                    d_anno_y["s"].append(s)
                    d_anno_y["e"].append(s + e)
                    d_anno_y["c"].append(Category10[10][idx % 10])

        def mmax(*args):
            m = 0
            for x in args:
                if not x is None and x > m:
                    m = x
            return m

        self.anno_x.x_range.factors = self.displayed_annos.value
        self.anno_y.y_range.factors = self.displayed_annos.value

        self.curr_bin_size.text="Current Bin Size:" + str(h_bin)

        self.raw_x_axis.xaxis.bounds = (0, mmax(*raw_x_heat, *raw_x_norm))
        self.ratio_x_axis.xaxis.bounds = (0, mmax(*raw_x_ratio))
        self.raw_y_axis.yaxis.bounds = (0, mmax(*raw_y_heat, *raw_y_norm))
        self.ratio_y_axis.yaxis.bounds = (0, mmax(*raw_y_ratio))

        self.heatmap.background_fill_color = b_col
        self.heatmap_data.data = d_heatmap
        self.raw_data_x.data = raw_data_x
        self.raw_data_y.data = raw_data_y
        
        self.anno_x_data.data = d_anno_x
        self.anno_y_data.data = d_anno_y

    def setup(self):
        if os.path.exists(self.meta_file.value + ".meta"):
            self.meta = MetaData.load(self.meta_file.value + ".meta")
            self.meta.setup(self)
            if os.path.exists(self.meta_file.value + ".heat.db.idx") and \
                        os.path.exists(self.meta_file.value + ".heat.db.dat"):
                self.idx = Tree_4(self.meta_file.value + ".heat.db")
                if os.path.exists(self.meta_file.value + ".norm.db.idx") and \
                            os.path.exists(self.meta_file.value + ".norm.db.dat"):
                    self.idx_norm = Tree_3(self.meta_file.value + ".norm.db")
                    self.trigger_render()

    def trigger_render(self):
        self.force_render = True

    def render_callback(self):
        if self.do_render:
            if not None in (self.heatmap.x_range.start, self.heatmap.x_range.end, self.heatmap.y_range.start, 
                            self.heatmap.y_range.end):
                curr_area = (self.heatmap.x_range.start, self.heatmap.y_range.start, 
                                self.heatmap.x_range.end, self.heatmap.y_range.end)
                w = curr_area[2] - curr_area[0]
                h = curr_area[3] - curr_area[1]
                curr_area_size = w*h
                min_change = 1-self.redraw_slider.value/100
                #print(overlap)
                if curr_area_size / self.curr_area_size < min_change or self.force_render or \
                            MainLayout.area_outside(self.last_drawing_area, curr_area):
                    if curr_area_size / self.curr_area_size < min_change:
                        print("rendering due to zoom in", curr_area_size / self.curr_area_size)
                    if self.force_render:
                        print("rendering forced")
                    if MainLayout.area_outside(self.last_drawing_area, curr_area):
                        print("rendering due to pan", self.last_drawing_area, curr_area)
                    self.force_render = False
                    self.curr_area_size = curr_area_size
                    x = self.add_area_slider.value/100
                    new_area = (curr_area[0] - w*x, curr_area[1] - h*x,
                                curr_area[2] + w*x, curr_area[3] + h*x)
                    self.last_drawing_area = new_area
                    self.curr_bin_size.text="Rendering..."
                    def callback():
                        self.render(new_area)
                        self.curdoc.add_timeout_callback(lambda: self.render_callback(), self.update_frequency_slider.value*1000)
                    self.curdoc.add_next_tick_callback(callback)
                    return

            self.curdoc.add_timeout_callback(lambda: self.render_callback(), self.update_frequency_slider.value*1000)

    def set_root(self):
        self.curdoc.clear()
        self.curdoc.add_root(self.root)
        self.do_render = True
        self.force_render = True
        self.render_callback()
