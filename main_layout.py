__author__ = "Markus Schmidt"
__version__ = "0.0.3"
__email__ = "Markus.Schmidt@lmu.de"

from bokeh.layouts import grid, row, column
from bokeh.plotting import figure, curdoc
from bokeh.models.tools import ToolbarBox, ProxyToolbar
from bokeh.models import ColumnDataSource, Dropdown, Button, RangeSlider, Slider, TextInput, MultiChoice, FuncTickFormatter, Div, HoverTool, Toggle
import math
from datetime import datetime
from tornado import gen
from bokeh.document import without_document_lock
from bokeh.models import Panel, Tabs, Spacer
from bokeh.models import Range1d
from meta_data import *
import os
from heatmap_as_r_tree import *
from bokeh.palettes import Viridis256, Colorblind
from datetime import datetime, timedelta
import psutil
from concurrent.futures import ThreadPoolExecutor
from bokeh.models import BoxAnnotation
from stats import *
from bokeh.models.tickers import AdaptiveTicker

SETTINGS_WIDTH = 200
DEFAULT_SIZE = 50
ANNOTATION_PLOT_NAME = "Annotation"
RATIO_PLOT_NAME = "Ratio"
RAW_PLOT_NAME = "Cov"

DIV_MARGIN = (5, 5, 0, 5)

executor = ThreadPoolExecutor(max_workers=1)


class FigureMaker:
    _show_hide = {"grid_lines": True}
    _hidable_plots = []
    _plots = []
    _unhide_button = None
    render_areas = {}

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
        ret.yaxis.axis_label = self.y_axis_label
        ret.xaxis.axis_label = self.x_axis_label
        if not self.toolbar_list is None:
            self.toolbar_list.append(ret.toolbar)
            ret.toolbar_location = None
        if len(self._hide_on) > 0:
            FigureMaker._hidable_plots.append((ret, self._hide_on))
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
        ret.xgrid.level = "glyph"
        ret.ygrid.level = "glyph"
        ret.background_fill_color = "lightgrey"
        render_area = BoxAnnotation(fill_alpha=1, top=0, bottom=0, fill_color='white', level="image")
        ret.add_layout(render_area)
        FigureMaker.render_areas[ret] = render_area
        FigureMaker._plots.append(ret)
        return ret

    @staticmethod
    def plot_render_area(plot):
        return FigureMaker.render_areas[plot]

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
        #self.args["height_policy"] = "min"
        self.args["height"] = 10
        self.no_border_v = True
        return self

    def link_x(self, other):
        self.args["x_range"] = other.x_range
        #self.args["sizing_mode"] = "stretch_width"
        self.args["width_policy"] = "fit"
        self.args["width"] = None
        self.no_border_h = True
        return self

    def stretch(self):
        self.args["sizing_mode"] = "stretch_both"
        #self.args["width_policy"] = "fit"
        #self.args["height_policy"] = "max"
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
        if other.sizing_mode in ["stretch_both", "stretch_width"] or other.width_policy in ["fit", "max"]:
            #self.args["sizing_mode"] = "stretch_width"
            self.args["width_policy"] = "fit"
            self.w(None)
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
        if other.sizing_mode in ["stretch_both", "stretch_height"] or other.height_policy in ["fit", "max"]:
            self.args["sizing_mode"] = "stretch_height"
            #self.args["height_policy"] = "max"
            self.h(10)
        else:
            self.h(other.height)
            self.args["sizing_mode"] = "fixed"
        self.args["align"] = "end"
        self.y_axis_label = label
        self.no_border_h = True
        return self

    def categorical_x(self):
        self.args["x_range"] = [""]
        return self

    def categorical_y(self):
        self.args["y_range"] = [""]
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
        tools = sum([toolbar.tools for toolbar in tools_list], [])
        proxy = ProxyToolbar(toolbars=tools_list,
                             tools=tools, **toolbar_options)
        proxy.logo = None
        return ToolbarBox(toolbar=proxy, toolbar_location=toolbar_location)

    @staticmethod
    def update_visibility():
        for plot, keys in FigureMaker._hidable_plots:
            visible = True
            for key in keys:
                if not FigureMaker._show_hide[key]:
                    visible = False
                    break
            if plot.visible != visible:
                plot.visible = visible
        if not FigureMaker._unhide_button is None:
            if FigureMaker._unhide_button.visible == FigureMaker._show_hide["tools"]:
                FigureMaker._unhide_button.visible = not FigureMaker._show_hide["tools"]
        c = "darkgrey" if FigureMaker._show_hide["grid_lines"] else None
        c2 = "lightgrey" if FigureMaker._show_hide["grid_lines"] else None
        for plot in FigureMaker._plots:
            if plot.grid.grid_line_color != c:
                plot.grid.grid_line_color = c
                plot.grid.minor_grid_line_color = c2

    @staticmethod
    def toggle_hide(key):
        FigureMaker._show_hide[key] = not FigureMaker._show_hide[key]
        FigureMaker.update_visibility()

    @staticmethod
    def is_visible(key):
        return FigureMaker._show_hide[key]

    @staticmethod
    def show_hide_dropdown(*names):
        for _, key in names:
            if key not in FigureMaker._show_hide:
                FigureMaker._show_hide[key] = True

        def make_menu():
            menu = []
            for name, key in names:
                menu.append(
                    (("☑ " if FigureMaker._show_hide[key] or key == "tools" else "☐ ") + name, key))
            menu.append(
                (("☑ " if FigureMaker._show_hide[key] else "☐ ") + "Grid Lines", "grid_lines"))
            return menu
        ret = Dropdown(label="Show/Hide", menu=make_menu(),
                       width=SETTINGS_WIDTH, sizing_mode="stretch_width")

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
        ret = Dropdown(label=title, menu=make_menu(), width=SETTINGS_WIDTH, sizing_mode="stretch_width")

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
        self.cancel_render = False
        self.force_render = True
        self.curdoc = curdoc()
        self.last_drawing_area = (0, 0, 0, 0)
        self.curr_area_size = 1
        self.idx = None
        self.idx_norm = None
        self.render_curr_step = 0
        self.render_reason = ""
        self.render_last_step = None
        self.render_time_record = []

        global SETTINGS_WIDTH
        tollbars = []
        self.heatmap = FigureMaker().range1d().stretch().combine_tools(tollbars).get()

        d = {"b": [], "l": [], "t": [], "r": [], "c": [], "chr_x": [], "chr_y": [], "x1": [], "x2": [],
             "y1": [], "y2": [], "s": [], "d_a": [], "d_b": [], 'info': []}
        self.heatmap_data = ColumnDataSource(data=d)
        self.heatmap.quad(left="l", bottom="b", right="r", top="t", fill_color="c", line_color=None,
                          source=self.heatmap_data, level="underlay")


        self.heatmap.add_tools(HoverTool(
            tooltips=[
                ('(x, y)', "(@chr_x @x1 - @x2, @chr_y @y1 - @y2)"),
                ('score', "@s"),
                ('reads by group', "A: @d_a, B: @d_b"),
                ('info', '@info')
            ]
        ))

        self.heatmap_x_axis = FigureMaker().x_axis_of(
            self.heatmap, "DNA").combine_tools(tollbars).get()
        self.heatmap_y_axis = FigureMaker().y_axis_of(
            self.heatmap, "RNA").combine_tools(tollbars).get()

        ratio_hover_x = HoverTool(
            tooltips=[
                ('pos', "@chr @pos1 - @pos2"),
                ('row sum', '@heat'),
                ('normalization', '@norm'),
                ('ratio', '@ratio'),
            ],
            mode='hline'
        )
        ratio_hover_y = HoverTool(
            tooltips=[
                ('pos', "@chr @pos1 - @pos2"),
                ('col sum', '@heat'),
                ('normalization', '@norm'),
                ('ratio', '@ratio'),
            ],
            mode='vline'
        )

        self.ratio_x = FigureMaker().w(DEFAULT_SIZE).link_y(
            self.heatmap).hide_on("ratio").combine_tools(tollbars).get()
        self.ratio_x.add_tools(ratio_hover_x)
        self.ratio_x_axis = FigureMaker().x_axis_of(
            self.ratio_x).combine_tools(tollbars).get()
        self.ratio_x_axis.xaxis.axis_label = "Ratio"
        self.ratio_x_axis.xaxis.ticker.desired_num_ticks = 3

        self.ratio_y = FigureMaker().h(DEFAULT_SIZE).link_x(
            self.heatmap).hide_on("ratio").combine_tools(tollbars).get()
        self.ratio_y.add_tools(ratio_hover_y)
        self.ratio_y_axis = FigureMaker().y_axis_of(
            self.ratio_y).combine_tools(tollbars).get()
        self.ratio_y_axis.yaxis.axis_label = "Ratio"
        self.ratio_y_axis.yaxis.ticker.desired_num_ticks = 3


        raw_hover_x = HoverTool(
            tooltips="""
                <div>
                    <span style="color: @cs">@ls: $data_x</span>
                </div>
            """,
            mode='hline'
        )
        raw_hover_y = HoverTool(
            tooltips="""
                <div>
                    <span style="color: @cs">@ls: $data_y</span>
                </div>
            """,
            mode='vline'
        )

        self.raw_x = FigureMaker().w(DEFAULT_SIZE).link_y(
            self.heatmap).hide_on("raw").combine_tools(tollbars).get()
        self.raw_x.add_tools(raw_hover_x)
        self.raw_x_axis = FigureMaker().x_axis_of(
            self.raw_x).combine_tools(tollbars).get()
        self.raw_x_axis.xaxis.axis_label = "Cov"
        self.raw_x_axis.xaxis.ticker = AdaptiveTicker(desired_num_ticks=3)
        self.raw_x_axis.xgrid.ticker = AdaptiveTicker(desired_num_ticks=3)

        self.raw_y = FigureMaker().h(DEFAULT_SIZE).link_x(
            self.heatmap).hide_on("raw").combine_tools(tollbars).get()
        self.raw_y.add_tools(raw_hover_y)
        self.raw_y_axis = FigureMaker().y_axis_of(
            self.raw_y).combine_tools(tollbars).get()
        self.raw_y_axis.yaxis.axis_label = "Cov"
        self.raw_y_axis.yaxis.ticker = AdaptiveTicker(desired_num_ticks=3)
        self.raw_y_axis.ygrid.ticker = AdaptiveTicker(desired_num_ticks=3)

        d_x = {
            "chr": [],
            "pos1": [],
            "pos2": [],
            "xs": [],
            "ys": [],
            "cs": [],
            "ls": [],
        }
        d_y = {
            "chr": [],
            "pos1": [],
            "pos2": [],
            "xs": [],
            "ys": [],
            "cs": [],
            "ls": [],
        }
        self.raw_data_x = ColumnDataSource(data=d_x)
        self.raw_data_y = ColumnDataSource(data=d_y)
        self.raw_x.multi_line(xs="ys", ys="xs", source=self.raw_data_x,
                        line_color="cs")  # , level="image"
        self.raw_y.multi_line(xs="xs", ys="ys", source=self.raw_data_y,
                        line_color="cs")  # , level="image"
        d_x = {
            "chr": [],
            "pos1": [],
            "pos2": [],
            "pos": [],
            "ratio": [],
        }
        d_y = {
            "chr": [],
            "pos1": [],
            "pos2": [],
            "pos": [],
            "ratio": [],
        }
        self.ratio_data_x = ColumnDataSource(data=d_x)
        self.ratio_data_y = ColumnDataSource(data=d_y)
        self.ratio_x.line(x="ratio", y="pos", source=self.ratio_data_x,
                          line_color="black")  # , level="image"
        self.ratio_y.line(x="pos", y="ratio", source=self.ratio_data_y,
                          line_color="black")  # , level="image"

        self.anno_x = FigureMaker().w(DEFAULT_SIZE).link_y(self.heatmap).hide_on(
            "annotation").combine_tools(tollbars).categorical_x().get()
        self.anno_x_axis = FigureMaker().x_axis_of(
            self.anno_x).combine_tools(tollbars).get()
        self.anno_x_axis.xaxis.axis_label = "Anno"

        self.anno_y = FigureMaker().h(DEFAULT_SIZE).link_x(self.heatmap).hide_on(
            "annotation").combine_tools(tollbars).categorical_y().get()
        self.anno_y_axis = FigureMaker().y_axis_of(
            self.anno_y).combine_tools(tollbars).get()
        self.anno_y_axis.yaxis.axis_label = "Anno"

        d = {"x": [], "s": [], "e": [], "c": [], "chr": [],
             "pos1": [], "pos2": [], "info": [], "n": []}
        self.anno_x_data = ColumnDataSource(data=d)
        self.anno_x.vbar(x="x", top="e", bottom="s", width=0.9, fill_color="c", line_color=None,
                         source=self.anno_x_data)
        self.anno_y_data = ColumnDataSource(data=d)
        self.anno_y.hbar(y="x", right="e", left="s", height=0.9, fill_color="c", line_color=None,
                         source=self.anno_y_data)

        anno_hover = HoverTool(
            tooltips=[
                ('bin pos', "@chr @pos1 - @pos2"),
                ('num_annotations', "@n"),
                ('info', "@info"),
            ]
        )
        self.anno_x.add_tools(anno_hover)
        self.anno_y.add_tools(anno_hover)

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
                                               ("Sum", "sum"), ("Show First Group", "1st"), (
                                                   "Show Second Group", "2nd"), ("Substract", "sub"),
                                               ("Difference", "dif"), ("Minimum", "min"), ("Maximum", "max"))

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
                                                  ("Largest Rendered Bin",
                                                   "max_bin_visible"),
                                                  ("Number of Reads",
                                                   "num_reads"), 
                                                   ("Column", "column"),
                                                   ("Row", "row"),
                                                  ("Coverage of Normalization Reads (Absolute)",
                                                   "tracks_abs"),
                                                  ("Coverage of Normalization Reads (Scaled to Rendered Area)", "tracks_rel"),
                                                  ("Emulate RADICL-seq", "radicl-seq"))

        def stretch_event(e):
            self.heatmap.sizing_mode = e
            if e == "stretch_both":
                self.settings.width_policy = "fixed"
            else:
                self.settings.width_policy = "max"
        self.stretch = self.dropdown_select("Stretch/Scale", stretch_event,
                                                  ("Stretch", "stretch_both"),
                                                  ("Scale", "scale_height"))

        self.mapq_slider = RangeSlider(width=SETTINGS_WIDTH, start=0, end=MAP_Q_MAX, value=(0, MAP_Q_MAX), step=1,
                                       title="Mapping Quality Bounds", sizing_mode="stretch_width")
        self.mapq_slider.on_change(
            "value_throttled", lambda x, y, z: self.trigger_render())

        self.interactions_bounds_slider = Slider(width=SETTINGS_WIDTH, start=0, end=100, value=0, step=1,
                                                 title="Color Scale Begin", sizing_mode="stretch_width")
        self.interactions_bounds_slider.on_change(
            "value_throttled", lambda x, y, z: self.trigger_render())

        self.interactions_slider = Slider(width=SETTINGS_WIDTH, start=-50, end=50, value=10, step=0.1,
                                          title="Color Scale Log Base", 
                                          sizing_mode="stretch_width")  # , format="0[.]000")
        self.interactions_slider.on_change(
            "value_throttled", lambda x, y, z: self.trigger_render())

        self.update_frequency_slider = Slider(width=SETTINGS_WIDTH, start=0.1, end=3, value=0.5, step=0.1,
                                              title="Update Frequency [seconds]", format="0[.]000"
                                              , sizing_mode="stretch_width")

        self.redraw_slider = Slider(width=SETTINGS_WIDTH, start=0, end=100, value=90, step=1,
                                    title="Redraw if zoomed in by [%]", sizing_mode="stretch_width")

        self.add_area_slider = Slider(width=SETTINGS_WIDTH, start=0, end=500, value=100, step=10,
                                      title="Additional Draw Area [%]", sizing_mode="stretch_width")
        self.add_area_slider.on_change(
            "value_throttled", lambda x, y, z: self.trigger_render())

        self.diag_dist_slider = Slider(width=SETTINGS_WIDTH, start=0, end=1000, value=0, step=1,
                                       title="Minimum Distance from Diagonal", sizing_mode="stretch_width")
        self.diag_dist_slider.on_change(
            "value_throttled", lambda x, y, z: self.trigger_render())

        self.anno_size_slider = Slider(width=SETTINGS_WIDTH, start=10, end=500, value=DEFAULT_SIZE, step=1,
                                       title=ANNOTATION_PLOT_NAME + " Plot Size", sizing_mode="stretch_width")

        def anno_size_slider_event(attr, old, new):
            self.anno_x.width = self.anno_size_slider.value
            self.anno_x_axis.width = self.anno_size_slider.value
            self.anno_y.height = self.anno_size_slider.value
            self.anno_y_axis.height = self.anno_size_slider.value
        self.anno_size_slider.on_change(
            "value_throttled", anno_size_slider_event)

        self.ratio_size_slider = Slider(width=SETTINGS_WIDTH, start=10, end=500, value=DEFAULT_SIZE, step=1,
                                        title=RATIO_PLOT_NAME + " Plot Size", sizing_mode="stretch_width")

        def ratio_size_slider_event(attr, old, new):
            self.ratio_x.width = self.ratio_size_slider.value
            self.ratio_x_axis.width = self.ratio_size_slider.value
            self.ratio_y.height = self.ratio_size_slider.value
            self.ratio_y_axis.height = self.ratio_size_slider.value
        self.ratio_size_slider.on_change(
            "value_throttled", ratio_size_slider_event)

        self.raw_size_slider = Slider(width=SETTINGS_WIDTH, start=10, end=500, value=DEFAULT_SIZE, step=1,
                                      title=RAW_PLOT_NAME + " Plot Size", sizing_mode="stretch_width")

        def raw_size_slider_event(attr, old, new):
            self.raw_x.width = self.raw_size_slider.value
            self.raw_x_axis.width = self.raw_size_slider.value
            self.raw_y.height = self.raw_size_slider.value
            self.raw_y_axis.height = self.raw_size_slider.value
        self.raw_size_slider.on_change(
            "value_throttled", raw_size_slider_event)

        self.num_bins = Slider(width=SETTINGS_WIDTH, start=10000, end=1000000, value=60000, step=10000,
                               title="Number of Bins", sizing_mode="stretch_width")
        self.num_bins.on_change(
            "value_throttled", lambda x, y, z: self.trigger_render())
            
        meta_file_label = Div(text="Data path:")
        meta_file_label.margin = DIV_MARGIN
        self.meta_file = TextInput(value="heatmap_server/out/")
        self.meta_file.on_change("value", lambda x, y, z: self.setup())

        self.group_a = MultiChoice(value=[], options=[],
                                   placeholder="Group A")
        self.group_a.on_change("value", lambda x, y, z: self.trigger_render())
        self.group_b = MultiChoice(value=[], options=[],
                                   placeholder="Group B")
        self.group_b.on_change("value", lambda x, y, z: self.trigger_render())

        div_displayed_annos = Div(text="Displayed Annotations:")
        div_displayed_annos.margin = DIV_MARGIN
        self.displayed_annos = MultiChoice(value=[], options=[])
        self.displayed_annos.on_change(
            "value", lambda x, y, z: self.trigger_render())
        div_filtered_annos_x = Div(text="Filter rows that overlap with:")
        div_filtered_annos_x.margin = DIV_MARGIN
        self.filtered_annos_x = MultiChoice(value=[], options=[])
        self.filtered_annos_x.on_change(
            "value", lambda x, y, z: self.trigger_render())
        div_filtered_annos_y = Div(text="Filter columns that overlap with:")
        div_filtered_annos_y.margin = DIV_MARGIN
        self.filtered_annos_y = MultiChoice(value=[], options=[])
        self.filtered_annos_y.on_change(
            "value", lambda x, y, z: self.trigger_render())

        power_tick = FuncTickFormatter(
            code="""
            if (tick / 9 >= 7)
                return Math.ceil((1 + tick % 9)) + "*10^" + Math.floor(tick / 9) + "bp";
            else if (tick / 9 >= 3)
                return Math.ceil((1 + tick % 9) * Math.pow(10, Math.floor(tick / 9)-3)) + "kbp";
            else
                return Math.ceil((1 + tick % 9) * Math.pow(10, Math.floor(tick / 9))) + "bp"; """)
        self.min_max_bin_size = RangeSlider(start=0, end=9*15, value=(0, 9*6), step=1, title="Bin Size Bounds [nt]",
                                            format=power_tick)
        self.min_max_bin_size.on_change(
            "value_throttled", lambda x, y, z: self.trigger_render())

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
        self.norm_x.on_change("value", lambda x, y, z: self.trigger_render())
        self.norm_y = MultiChoice(value=[], options=[])
        self.norm_y.on_change("value", lambda x, y, z: self.trigger_render())

        self.info_div = Div(text="n/a", style={"word-break": "break-all", "max-width": str(
            SETTINGS_WIDTH)+"px"}, width=SETTINGS_WIDTH, sizing_mode="stretch_width")

        clear_annos_button = Button(label="clear all displayed annotations")
        def event(e):
            self.displayed_annos.value = []
        clear_annos_button.on_click(event)
        clear_filter_annos_button = Button(label="clear all filter annotations")
        def event(e):
            self.filtered_annos_x.value = []
            self.filtered_annos_y.value = []
        clear_filter_annos_button.on_click(event)

        def make_panel(title, children):
            t = Toggle(active=False, button_type="light")

            r = column([t] + children, sizing_mode="stretch_width")
            def callback(e):
                if t.active:
                    p = "▿ "
                else:
                    p = "▸ "
                t.label = p + title
                for c in children:
                    c.visible = t.active
            t.on_click(callback)
            callback(None)
            return r

        _settings = column([
                make_panel("General", [tool_bar, self.meta_file, show_hide, self.symmetrie, self.diag_dist_slider,
                                    self.min_max_bin_size, self.curr_bin_size]),
                make_panel("Normalization", [self.normalization, self.mapq_slider, self.interactions_bounds_slider,
                                    self.interactions_slider, div_norm_x, self.norm_x, div_norm_y, self.norm_y]),
                make_panel("Replicates", [self.in_group, self.betw_group, div_group_a, self.group_a, div_group_b, self.group_b]),
                make_panel("GUI", [self.num_bins, self.update_frequency_slider, self.redraw_slider,
                                    self.add_area_slider,
                                    self.anno_size_slider, self.raw_size_slider, self.ratio_size_slider,
                                    self.stretch]),
                make_panel("Annotation", [div_displayed_annos, self.displayed_annos, clear_annos_button,
                                          div_filtered_annos_x, self.filtered_annos_x, 
                                          div_filtered_annos_y, self.filtered_annos_y, clear_filter_annos_button]),
                make_panel("Info", [self.info_div]),
            ],
            sizing_mode="stretch_both"
        )

        FigureMaker._hidable_plots.append((_settings, ["tools"]))
        sp = Spacer()
        sp.width = 20
        sp.width_policy = "fixed"
        self.settings = row([_settings, FigureMaker.reshow_settings(), sp],
                       css_classes=["full_height"])
        self.settings.height = 100
        self.settings.min_height = 100
        self.settings.height_policy = "fixed"
        self.settings.width = SETTINGS_WIDTH
        self.settings.width_policy = "fixed"

        grid_layout = [
            [self.heatmap_y_axis, self.anno_x,   self.raw_x,
                self.ratio_x,      None,              self.heatmap,   self.settings],
            [None,              self.anno_x_axis, self.raw_x_axis,
                self.ratio_x_axis, None,              None,               None],
            [None,              None,             None,            None,
                self.ratio_y_axis, self.ratio_y,       None],
            [None,              None,             None,            None,
                self.raw_y_axis,   self.raw_y,         None],
            [None,              None,             None,            None,
                self.anno_y_axis,  self.anno_y,        None],
            [None,              None,             None,            None,
                None,            self.heatmap_x_axis, None],
        ]

        self.root = grid(grid_layout) # , sizing_mode="stretch_both"

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

    def bin_cols_or_rows(self, area, h_bin, base_idx=0, none_for_chr_border=False, filter_annos=[]):
        ret = []
        ret_2 = []
        for pos_1, pos_2 in zip(*self.meta.chr_sizes.bin_cols_or_rows(h_bin, area[base_idx], 
                                                                      area[base_idx+2], none_for_chr_border)):
            not_filtered = True
            if not pos_1 is None and len(filter_annos) > 0:
                p, s = pos_1
                for anno_name in filter_annos:
                    if self.meta.annotations[anno_name].count(p, p+s) > 0:
                        not_filtered = False
                        break
            if not_filtered:
                ret.append(pos_1)
                ret_2.append(pos_2)
        return ret, ret_2

    def bin_cols(self, area, h_bin, none_for_chr_border=False, filter_l=None):
        if filter_l is None:
            filter_l = self.filtered_annos_y.value
        return self.bin_cols_or_rows(area, h_bin, 0, none_for_chr_border, filter_l)

    def bin_rows(self, area, h_bin, none_for_chr_border=False, filter_l=None):
        if filter_l is None:
            filter_l = self.filtered_annos_x.value
        return self.bin_cols_or_rows(area, h_bin, 1, none_for_chr_border, filter_l)

    def bin_coords(self, area, h_bin):
        h_bin = max(1, h_bin)
        ret = []
        ret_2 = []
        a, a_2 = self.bin_cols(area, h_bin)
        b, b_2 = self.bin_rows(area, h_bin)
        for (x, w), (x_chr, x_2) in zip(a, a_2):
            for (y, h), (y_chr, y_2) in zip(b, b_2):
                ret.append((x, y, w, h))
                ret_2.append((x_chr, x_2, y_chr, y_2))
        return ret, a, b, ret_2, a_2, b_2

    def make_bins(self, h_bin, bin_coords, name="make_bins"):
        bins = []
        info = [""]*len(bin_coords)
        min_ = self.interactions_bounds_slider.value
        for idx, _ in enumerate(self.meta.datasets):
            bins.append([])
            for idx_2, (x, y, w, h) in enumerate(bin_coords):
                self.render_step_log(name, idx_2 + idx * len(bin_coords), len(bin_coords)*len(self.meta.datasets))
                if abs(x - y) >= self.diag_dist_slider.value:
                    n = self.idx.count(idx, y, y+h, x, x+w, *self.mapq_slider.value)
                    bins[-1].append(max(n-min_, 0))
                    if n <= 10:
                        info[idx_2] += self.idx.info(idx, y, y+h, x, x+w, *self.mapq_slider.value)
                else:
                    bins[-1].append(0)
                if self.cancel_render:
                    print("RENDER CANCELED")
                    return None
        return bins, info

    def col_norm(self, h_bin, cols):
        x = self.make_bins(h_bin, [(c[0], 0, c[1], self.meta.chr_sizes.chr_start_pos["end"])
                                        if not c is None else (-2, -2, 1, 1) for c in cols], name="make_col_norm_bins")
        if x is None:
            return None
        return self.flatten_bins(x[0])

    def row_norm(self, h_bin, rows):
        x = self.make_bins(h_bin, [(0, c[0], self.meta.chr_sizes.chr_start_pos["end"], c[1])
                                        if not c is None else (-2, -2, 1, 1) for c in rows], name="make_row_norm_bins")
        if x is None:
            return None
        return self.flatten_bins(x[0])

    def read_norm(self, idx):
        n = []
        for idx, dataset in enumerate(self.meta.datasets):
            # @todo replace with query over entire dataset
            if str(idx) in (self.group_a.value if idx == 0 else self.group_b.value):
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
            [self.idx_norm.count(int(idx), 0, self.meta.chr_sizes.chr_start_pos["end"], *self.mapq_slider.value) \
                if self.meta.norm_via_tree(int(idx)) \
                else self.meta.norm[int(idx)].count(0, self.meta.chr_sizes.chr_start_pos["end"]) \
                for idx in (self.norm_x.value if rows else self.norm_y.value)]])[0]

    def norm_bins(self, h_bin, bins_l, cols, rows):
        ret = []
        if self.normalization_d in ["tracks_abs", "tracks_rel"]:
            raw_x_norm = self.linear_bins_norm(rows, True)
            raw_y_norm = self.linear_bins_norm(cols, False)
        if self.normalization_d in ["column"]:
            ns = self.col_norm(h_bin, cols)
        if self.normalization_d in ["row", "radicl-seq"]:
            ns = self.row_norm(h_bin, rows)
        for idx, bins in enumerate(bins_l):
            self.render_step_log("norm_bins", idx, len(bins_l))
            if self.normalization_d == "max_bin_visible":
                n = max(bins + [1])
                ret.append([x/n for x in bins])
            elif self.normalization_d == "num_reads":
                n = self.read_norm(idx)
                ret.append([x/n for x in bins])
            elif self.normalization_d == "column":
                ret.append([x/max(ns[idx][idx_2 // len(rows)], 1) for idx_2, x in enumerate(bins)])
            elif self.normalization_d == "row":
                ret.append([x/max(ns[idx][idx_2 % len(rows)], 1) for idx_2, x in enumerate(bins)])
            elif self.normalization_d == "radicl-seq":
                ret.append([])
                for idx_2 in range(len(rows)):
                    row = bins[idx_2::len(rows)]
                    ret[-1].extend(radicl_seq_norm(row, ns[idx][idx_2], h_bin, 
                                                   self.meta.chr_sizes.chr_start_pos["end"]))
            elif self.normalization_d in ["tracks_abs", "tracks_rel"]:
                n = self.read_norm(idx)

                def get_norm(i):
                    d = (raw_y_norm[i // len(rows)] *
                         raw_x_norm[i % len(rows)] * n)
                    if d == 0:
                        return 0
                    return (self.norm_num_reads(True) * self.norm_num_reads(False)) / d
                ret.append([x*get_norm(idx_2) for idx_2, x in enumerate(bins)])
                if self.normalization_d == "tracks_rel":
                    _max = max(*ret[-1], 0)
                    if _max > 0:
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
            self.render_step_log("flatten_bins", idx, len(bins[0]))
            a = []
            b = []
            for idx_2 in range(len(bins)):
                if str(idx_2) in self.group_a.value:
                    a.append(bins[idx_2][idx])
                if str(idx_2) in self.group_b.value:
                    b.append(bins[idx_2][idx])
            if self.in_group_d == "min":
                aa = min(a) if len(a) > 0 else 0
                bb = min(b) if len(b) > 0 else 0
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

    # used function:
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
            elif self.betw_group_d == "max":
                c = max(x, y)
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
                c = max(0, min(MAP_Q_MAX-1, int((MAP_Q_MAX-1)*c)))
                ret.append(Viridis256[c])
            else:
                ret.append(
                    Viridis256[max(0, min(MAP_Q_MAX-1, int((MAP_Q_MAX-1)*self.log_scale(c))))])
        return ret

    def color_bins(self, bins):
        return self.color_bins_b(self.color_bins_a(bins))

    def purge(self, background, *bins):
        ret = tuple(([] for _ in bins))
        for xs in zip(*bins):
            if xs[0] != background:
                for idx, x in enumerate(xs):
                    ret[idx].append(x)
        return ret

    def bin_symmentry(self, h_bin, bins, bin_coords, bin_cols, bin_rows):
        if self.symmetrie_d == "all":
            return bins
        elif self.symmetrie_d == "sym" or self.symmetrie_d == "asym":
            x = self.make_bins(h_bin, [(y, x, h, w) for x, y, w, h in bin_coords], name="make_bins_symmetrie")
            if x is None:
                return None
            bins_2, _ = x
            norms = self.norm_bins(h_bin, bins_2, bin_rows, bin_cols)
            if self.symmetrie_d == "sym":
                return [[min(a, b) for a, b in zip(bin, norm)] for bin, norm in zip(bins, norms)]
            else:
                return [[max(a-b, 0) for a, b in zip(bin, norm)] for bin, norm in zip(bins, norms)]
        else:
            raise RuntimeError("Unknown symmetry value")

    def annotation_bins(self, bins, coverage_obj):
        return [coverage_obj.count(x[0], x[0] + x[1]) if not x is None else float('NaN') for x in bins]

    def linear_bins_norm(self, bins, rows):
        vals = [
            [self.idx_norm.count(int(idx), x[0], x[0] + x[1], *self.mapq_slider.value) \
                if self.meta.norm_via_tree(int(idx)) else self.meta.norm[int(idx)].count(x[0], x[0] + x[1]) \
                for idx in (self.norm_x.value if rows else self.norm_y.value)]
            if not x is None else [float('NaN')] for x in bins]
        return self.flatten_norm(vals), vals

    def new_render(self, reason):
        self.render_curr_step = 0
        self.render_time_record = []
        if not reason is None:
            self.render_reason = reason
            self.render_step_log()

    def render_step_log(self, step_name="", sub_step=0, sub_step_total=None):
        if self.render_last_step is None or self.render_last_step != step_name:
            self.render_last_step = step_name
            if self.render_last_step != step_name:
                self.render_curr_step += 1
            if not len(step_name) == 0:
                if len(self.render_time_record) > 0:
                    self.render_time_record[-1][1] = datetime.now() - \
                        self.render_time_record[-1][1]
                self.render_time_record.append([step_name, datetime.now()])
        modulo = 1000
        if not sub_step_total is None:
            modulo = sub_step_total / 100
        if sub_step % modulo == 0:
            s = "rendering due to " + self.render_reason + "."
            if len(step_name) > 0:
                s += " Step " + str(self.render_curr_step) + \
                    " " + str(step_name) + ". Substep " + str(sub_step)
                if not sub_step_total is None:
                    s += " of " + str(sub_step_total) + ". "
                if len(self.render_time_record) > 0:
                    s += " Runtime: " + str(datetime.now() - self.render_time_record[-1][1])
            print(s, end="\033[K\r")

            def callback():
                self.curr_bin_size.text = s.replace(". ", "<br>")
            self.curdoc.add_next_tick_callback(callback)

    def render_done(self, bin_amount):
        if len(self.render_time_record) > 0:
            self.render_time_record[-1][1] = datetime.now() - \
                self.render_time_record[-1][1]
        print("render done, used time:\033[K")
        total_time = timedelta()
        for x in self.render_time_record:
            total_time += x[1]
        for idx, (name, time) in enumerate(self.render_time_record):
            print("step " + str(idx), str(time),
                  str(int(100*time/total_time)) + "%", name, "\033[K", sep="\t")
        print("Currently used RAM:", psutil.virtual_memory().percent, "%\033[K")
        print("Number of displayed bins:", bin_amount, "\033[K")

    @gen.coroutine
    @without_document_lock
    def render(self, area):
        def unlocked_task():
            self.cancel_render = False
            if self.meta is None or self.idx is None:
                def callback():
                    self.curr_bin_size.text = "Waiting for Fileinput."
                self.curdoc.add_next_tick_callback(callback)
                self.curdoc.add_timeout_callback(
                    lambda: self.render_callback(), self.update_frequency_slider.value*1000)
                return
            area_bin = (area[2] - area[0]) * \
                (area[3] - area[1]) / self.num_bins.value

            def power_of_ten(x):
                n = 0
                while True:
                    for i in [1, 1.25, 2.5, 5]:
                        if i*10**n >= x:
                            return i*10**n
                    n += 1
            h_bin = power_of_ten(math.sqrt(area_bin))
            def comp_bin_size(idx):
                t = self.min_max_bin_size.value[idx]
                return math.ceil((1 + t % 9) * 10**(t // 9))
            h_bin = min(max(h_bin, comp_bin_size(0)), comp_bin_size(1))

            area[0] -= area[0] % h_bin # align to nice and even number
            area[1] -= area[1] % h_bin # align to nice and even number
            area[2] += h_bin - (area[2] % h_bin) # align to nice and even number
            area[3] += h_bin - (area[3] % h_bin) # align to nice and even number

            bin_coords, bin_cols, bin_rows, bin_coords_2, bin_cols_2, bin_rows_2 = self.bin_coords(area, h_bin)
            print("bin_size", h_bin, "\033[K")
            bins, info = self.make_bins(h_bin, bin_coords)
            flat = self.flatten_bins(bins)
            norm = self.norm_bins(h_bin, flat, bin_cols, bin_rows)
            sym = self.bin_symmentry(h_bin, norm, bin_coords, bin_cols, bin_rows)
            c = self.color_bins(sym)
            b_col = Viridis256[(MAP_Q_MAX-1) //
                            2] if self.betw_group_d == "sub" else Viridis256[0]
            purged, purged_coords, purged_coords_2, purged_sym, purged_flat_a, purged_flat_b, purged_info = \
                self.purge(b_col, c, bin_coords, bin_coords_2,
                        self.color_bins_a(sym), *flat, info)

            norm_visible = FigureMaker.is_visible("raw") or FigureMaker.is_visible("ratio")

            if norm_visible:
                raw_bin_rows, raw_bin_rows_2 = self.bin_rows(area, h_bin, False)
                raw_bin_cols, raw_bin_cols_2 = self.bin_cols(area, h_bin, False)

                raw_x_norm_combined, raw_x_norms = self.linear_bins_norm(raw_bin_rows, True)
                raw_y_norm_combined, raw_y_norms = self.linear_bins_norm(raw_bin_cols, False)
                raw_x_heat = self.color_bins_a(self.row_norm(h_bin, raw_bin_rows))
                raw_y_heat = self.color_bins_a(self.col_norm(h_bin, raw_bin_cols))
                raw_x_ratio = [a/b if not b == 0 else 0 for a,
                            b in zip(raw_x_heat, raw_x_norm_combined)]
                raw_y_ratio = [a/b if not b == 0 else 0 for a,
                            b in zip(raw_y_heat, raw_y_norm_combined)]
            else:
                raw_bin_rows, raw_bin_rows_2 = ([], [])
                raw_bin_cols, raw_bin_cols_2 = ([], [])

                raw_x_norm_combined = []
                raw_x_norms = [[]]
                raw_y_norm_combined = []
                raw_y_norms = [[]]
                raw_x_heat = []
                raw_y_heat = []
                raw_x_ratio = []
                raw_y_ratio = []

            self.render_step_log("setup_col_data_sources")
            d_heatmap = {
                "b": [x[1] for x in purged_coords],
                "l": [x[0] for x in purged_coords],
                "t": [x[1] + x[3] for x in purged_coords],
                "r": [x[0] + x[2] for x in purged_coords],
                "c": purged,
                "chr_x": [x[0] for x in purged_coords_2],
                "chr_y": [x[2] for x in purged_coords_2],
                "x1": [x[1] for x in purged_coords_2],
                "x2": [x[1] + y[2] for x, y in zip(purged_coords_2, purged_coords)],
                "y1": [x[3] for x in purged_coords_2],
                "y2": [x[3] + y[3] for x, y in zip(purged_coords_2, purged_coords)],
                "s": purged_sym,
                "d_a": purged_flat_a,
                "d_b": purged_flat_b,
                "info": [x for x in purged_info],
            }

            def double_up(l):
                return [x for x in l for _ in [0, 1]]

            x_pos = [p for x in raw_bin_rows for p in [x[0], x[0] + x[1]]]
            x_chr = [x[0] for x in raw_bin_rows_2 for _ in [0, 1]]
            x_pos1 = [x[1] for x in raw_bin_rows_2 for _ in [0, 1]]
            x_pos2 = [x[1] + y[1] for x, y in zip(raw_bin_rows_2, raw_bin_rows) for _ in [0, 1]]

            x_num_raw = 2 + (0 if len(raw_x_norms) == 0 else len(raw_x_norms[0]))

            y_pos = [p for x in raw_bin_cols for p in [x[0], x[0] + x[1]]]
            y_chr = [x[0] for x in raw_bin_cols_2 for _ in [0, 1]]
            y_pos1 = [x[1] for x in raw_bin_cols_2 for _ in [0, 1]]
            y_pos2 = [x[1] + y[1] for x, y in zip(raw_bin_cols_2, raw_bin_cols) for _ in [0, 1]]

            y_num_raw = 2 + len(raw_y_norms[0])

            x_ys = []
            for idx in range(x_num_raw-2):
                x_ys.append([])
                for x in raw_x_norms:
                    for _ in [0,1]:
                        x_ys[-1].append(x[idx])
            y_ys = []
            for idx in range(y_num_raw-2):
                y_ys.append([])
                for x in raw_y_norms:
                    for _ in [0,1]:
                        y_ys[-1].append(x[idx])

            raw_data_x = {
                "xs": [x_pos for _ in range(x_num_raw)],
                "chr": [x_chr for _ in range(x_num_raw)],
                "pos1": [x_pos1 for _ in range(x_num_raw)],
                "pos2": [x_pos2 for _ in range(x_num_raw)],
                "ys": [double_up(raw_x_heat), double_up(raw_x_norm_combined)] + x_ys,
                "ls": ["heatmap row sum", "combined"] + [self.meta.normalizations[int(idx)][0] for idx in self.norm_x.value],
                "cs": [Colorblind[8][idx % 8] for idx in range(x_num_raw)],
            }
            raw_data_y = {
                "xs": [y_pos for _ in range(y_num_raw)],
                "chr": [y_chr for _ in range(y_num_raw)],
                "pos1": [y_pos1 for _ in range(y_num_raw)],
                "pos2": [y_pos2 for _ in range(y_num_raw)],
                "ys": [double_up(raw_y_heat), double_up(raw_y_norm_combined)] + y_ys,
                "ls": ["heatmap col sum", "combined"] + [self.meta.normalizations[int(idx)][0] for idx in self.norm_y.value],
                "cs": [Colorblind[8][idx % 8] for idx in range(y_num_raw)],
            }
            ratio_data_x = {
                "pos": x_pos,
                "chr": x_chr,
                "pos1": x_pos1,
                "pos2": x_pos2,
                "ratio": [x for x in raw_x_ratio for _ in [0, 1]],
            }
            ratio_data_y = {
                "pos": y_pos,
                "chr": y_chr,
                "pos1": y_pos1,
                "pos2": y_pos2,
                "ratio": [x for x in raw_y_ratio for _ in [0, 1]],
            }

            d_anno_x = {
                "chr": [],
                "pos1": [],
                "pos2": [],
                "x": [],
                "s": [],
                "e": [],
                "c": [],
                "n": [],
                "info": [],
            }
            if FigureMaker.is_visible("annotation"):
                bin_rows_unfiltr, bin_rows_2_unfiltr = self.bin_rows(area, h_bin, filter_l=[])
                for idx, anno in enumerate(self.displayed_annos.value):
                    for rb_2, (s, e), x in zip(bin_rows_2_unfiltr, bin_rows_unfiltr,
                                            self.annotation_bins(bin_rows_unfiltr, self.meta.annotations[anno])):
                        if x > 0:
                            d_anno_x["chr"].append(rb_2[0])
                            d_anno_x["pos1"].append(rb_2[1])
                            d_anno_x["pos2"].append(rb_2[1] + e)
                            d_anno_x["n"].append(x)
                            d_anno_x["x"].append(anno)
                            d_anno_x["s"].append(s)
                            d_anno_x["e"].append(s + e)
                            d_anno_x["c"].append(Colorblind[8][idx % 8])
                            if x > 10:
                                d_anno_x["info"].append("n/a")
                            else:
                                d_anno_x["info"].append(self.meta.annotations[anno].info(s, s+e))

            d_anno_y = {
                "chr": [],
                "pos1": [],
                "pos2": [],
                "x": [],
                "s": [],
                "e": [],
                "c": [],
                "n": [],
                "info": [],
            }
            if FigureMaker.is_visible("annotation"):
                bin_cols_unfiltr, bin_cols_2_unfiltr = self.bin_cols(area, h_bin, filter_l=[])
                for idx, anno in enumerate(self.displayed_annos.value):
                    for rb_2, (s, e), x in zip(bin_cols_2_unfiltr, bin_cols_unfiltr,
                                            self.annotation_bins(bin_cols_unfiltr, self.meta.annotations[anno])):
                        if x > 0:
                            d_anno_y["chr"].append(rb_2[0])
                            d_anno_y["pos1"].append(rb_2[1])
                            d_anno_y["pos2"].append(rb_2[1] + e)
                            d_anno_y["n"].append(x)
                            d_anno_y["x"].append(anno)
                            d_anno_y["s"].append(s)
                            d_anno_y["e"].append(s + e)
                            d_anno_y["c"].append(Colorblind[8][idx % 8])
                            if x > 10:
                                d_anno_y["info"].append("n/a")
                            else:
                                d_anno_y["info"].append(self.meta.annotations[anno].info(s, s+e))

            self.render_step_log("transfer_data")

            def callback():
                def mmax(*args):
                    m = 0
                    for x in args:
                        if not x is None and x > m:
                            m = x
                    return m
                def mmin(*args):
                    m = 0
                    for x in args:
                        if not x is None and x < m:
                            m = x
                    return m
                if len(self.displayed_annos.value) == 0:
                    self.anno_x.x_range.factors = [""]
                    self.anno_y.y_range.factors = [""]
                else:
                    self.anno_x.x_range.factors = self.displayed_annos.value
                    self.anno_y.y_range.factors = self.displayed_annos.value

                self.curr_bin_size.text = "Redering Donen\nCurrent Bin Size:" + \
                    str(h_bin)

                self.raw_x_axis.xaxis.bounds = (mmin(*raw_x_heat, *raw_x_norm_combined), 
                                                mmax(*raw_x_heat, *raw_x_norm_combined))
                self.ratio_x_axis.xaxis.bounds = (0, mmax(*raw_x_ratio))
                self.raw_y_axis.yaxis.bounds = (mmin(*raw_y_heat, *raw_y_norm_combined), 
                                                mmax(*raw_y_heat, *raw_y_norm_combined))
                self.ratio_y_axis.yaxis.bounds = (0, mmax(*raw_y_ratio))

                def set_bounds(plot, left=None, right=None, top=None, bottom=None, color=None):
                    ra = FigureMaker.plot_render_area(plot)
                    ra.left = area[0] if left is None else left
                    ra.bottom = area[1] if bottom is None else bottom
                    ra.right = area[2] if right is None else right
                    ra.top =area[3] if top is None else top
                    if not color is None:
                        ra.fill_color = color

                set_bounds(self.raw_x, left=mmin(*raw_x_heat, *raw_x_norm_combined), 
                            right=mmax(*raw_x_heat, *raw_x_norm_combined))
                set_bounds(self.ratio_x, left=0, right=mmax(*raw_x_ratio))
                set_bounds(self.raw_y, bottom=mmin(*raw_y_heat, *raw_y_norm_combined),
                            top=mmax(*raw_y_heat, *raw_y_norm_combined))
                set_bounds(self.ratio_y, bottom=0, top=mmax(*raw_y_ratio))
                set_bounds(self.anno_x, left=None, right=None)
                set_bounds(self.anno_y, bottom=None, top=None)

                set_bounds(self.heatmap, color=b_col)

                self.heatmap_data.data = d_heatmap
                self.raw_data_x.data = raw_data_x
                self.raw_data_y.data = raw_data_y
                self.ratio_data_x.data = ratio_data_x
                self.ratio_data_y.data = ratio_data_y
                self.anno_x_data.data = d_anno_x
                self.anno_y_data.data = d_anno_y
                self.render_done(len(bins[0]))
                self.curdoc.add_timeout_callback(
                    lambda: self.render_callback(), self.update_frequency_slider.value*1000)
            self.curdoc.add_next_tick_callback(callback)

        yield executor.submit(unlocked_task)

    def setup(self):
        print("loading...\033[K")
        #if self.meta is None:
        #    bed_folder = "/work/project/ladsie_012/ABS.2.2/2021-10-26_NS502-NS521_ABS_CR_RADICL_inputMicroC/bed_files"
        #    bed_suffix = "RNA.sorted.bed_K1K2.bed_K4.bed_R_D.bed_R_D_K1K2.bed_R_D_PRE1.bed"
        #    bam_folder = "/work/project/ladsie_012/ABS.2.2/20210608_Inputs"
        #    bam_suffix="R1.sorted.bam"
        #    meta, tree, t_n = preprocess.preprocess(
        #        "", "out/mini", "heatmap_server/Lister427.sizes", 
        #        "heatmap_static/HGAP3_Tb427v10_merged_2021_06_21.gff3", [
        #        (bed_folder + "/NS504_P10_Total_3." + bed_suffix, "P10_Total_Rep3", "a"),
        #        (bed_folder + "/NS505_N50_Total_1." + bed_suffix, "P10_Total_Rep1", "a"),
        #        (bed_folder + "/NS508_P10_NPM_1." + bed_suffix, "P10_NPM_Rep1", "b"),
        #        (bed_folder + "/NS511_N50_NPM_1." + bed_suffix, "N50_NPM_Rep1", "b"),
        #    ], [
        #        (bam_folder + "/WT1_gDNA_inputATAC." + bam_suffix, "gDNA_inputATAC", "col"),
        #        (bam_folder + "/WT1_RNAseq_NS320." + bam_suffix, "RNAseq_NS320", "row"),
        #    ])
        #    self.meta = meta
        #    self.meta.setup(self)
        #    self.idx = tree
        #    self.idx_norm = t_n
        #    self.trigger_render()
        if True:
            if os.path.exists(self.meta_file.value + ".meta"):
                self.meta = MetaData.load(self.meta_file.value + ".meta")
                self.meta.setup(self)
                self.idx = Tree_4(self.meta_file.value)
                self.idx_norm = Tree_3(self.meta_file.value)
                print("done loading\033[K")
                self.trigger_render()
            else:
                print("File not found")

    def trigger_render(self):
        #print("TRIGGERING RENDER")
        #self.cancel_render = True
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
                # print(overlap)
                if curr_area_size / self.curr_area_size < min_change or self.force_render or \
                        MainLayout.area_outside(self.last_drawing_area, curr_area):
                    self.new_render("startup")
                    if curr_area_size / self.curr_area_size < min_change:
                        self.new_render("zoom")
                    if self.force_render:
                        self.new_render("setting change")
                    if MainLayout.area_outside(self.last_drawing_area, curr_area):
                        self.new_render("pan")
                    self.force_render = False
                    self.curr_area_size = curr_area_size
                    x = self.add_area_slider.value/100
                    new_area = [curr_area[0] - w*x, curr_area[1] - h*x,
                                curr_area[2] + w*x, curr_area[3] + h*x]
                    self.last_drawing_area = new_area

                    def callback():
                        self.render(new_area)
                    self.curdoc.add_next_tick_callback(callback)
                    return

            self.curdoc.add_timeout_callback(
                lambda: self.render_callback(), self.update_frequency_slider.value*1000)

    def set_root(self):
        self.curdoc.clear()
        self.curdoc.add_root(self.root)
        self.do_render = True
        self.force_render = True
        self.render_callback()
