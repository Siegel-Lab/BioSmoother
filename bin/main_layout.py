__author__ = "Markus Schmidt"
__version__ = "0.0.3"
__email__ = "Markus.Schmidt@lmu.de"

from bokeh.layouts import grid, row, column
from bokeh.plotting import figure, curdoc
from bokeh.models.tools import ToolbarBox, ProxyToolbar
from bokeh.models import ColumnDataSource, Dropdown, Button, RangeSlider, Slider, TextInput, MultiChoice, FuncTickFormatter, Div, HoverTool, Toggle, Box, Spinner
from bokeh.io import export_png, export_svg
import math
from datetime import datetime
from tornado import gen
from bokeh.document import without_document_lock
from bokeh.models import Panel, Tabs, Spacer, Slope, PreText, CustomJS
from bokeh.models import Range1d, ColorBar, ContinuousColorMapper
from bin.meta_data import *
import os
from bin.heatmap_as_r_tree import *
from bokeh.palettes import Viridis256, Colorblind, Plasma256, Turbo256, Greys256
from datetime import datetime, timedelta
import psutil
from concurrent.futures import ThreadPoolExecutor
from bokeh.models import BoxAnnotation
from bin.stats import *
from bokeh.models.tickers import AdaptiveTicker
import bin.libSps

SETTINGS_WIDTH = 400
DEFAULT_SIZE = 50
DROPDOWN_HEIGHT=30
ANNOTATION_PLOT_NAME = "Annotation"
RATIO_PLOT_NAME = "Ratio"
RAW_PLOT_NAME = "Cov"

DIV_MARGIN = (5, 5, 0, 5)
BTN_MARGIN = (3, 3, 3, 3)

executor = ThreadPoolExecutor(max_workers=1)


class FigureMaker:
    _show_hide = {"grid_lines": True, "indent_line": False}
    _hidable_plots = []
    _plots = []
    _unhide_button = None
    render_areas = {}
    _slope = None

    x_coords_d = "full_genome"
    y_coords_d = "full_genome"

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
        cx = ("darkgrey" if FigureMaker.x_coords_d == "full_genome" else "lightgrey") \
                if FigureMaker._show_hide["grid_lines"] else None
        cx2 = "lightgrey" if FigureMaker._show_hide["grid_lines"] and FigureMaker.x_coords_d == "full_genome" else None
        cy = ("darkgrey" if FigureMaker.y_coords_d == "full_genome" else "lightgrey") \
                if FigureMaker._show_hide["grid_lines"] else None
        cy2 = "lightgrey" if FigureMaker._show_hide["grid_lines"] and FigureMaker.y_coords_d == "full_genome" else None
        FigureMaker._slope.line_color = "darkgrey" if FigureMaker._show_hide["indent_line"] else None
        for plot in FigureMaker._plots:
            if plot.xgrid.grid_line_color != cx:
                plot.xgrid.grid_line_color = cx
                plot.xgrid.minor_grid_line_color = cx2
            if plot.ygrid.grid_line_color != cy:
                plot.ygrid.grid_line_color = cy
                plot.ygrid.minor_grid_line_color = cy2

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
                (("☑ " if FigureMaker._show_hide["grid_lines"] else "☐ ") + "Grid Lines", "grid_lines"))
            menu.append(
                (("☑ " if FigureMaker._show_hide["indent_line"] else "☐ ") + "Identity Line", "indent_line"))
            return menu
        ret = Dropdown(label="Show/Hide", menu=make_menu(),
                       width=SETTINGS_WIDTH, sizing_mode="fixed", css_classes=["other_button", "tooltip", "tooltip_show_hide"], height=DROPDOWN_HEIGHT)

        def event(e):
            FigureMaker.toggle_hide(e.item)
            ret.menu = make_menu()
        ret.on_click(event)
        return ret

    @staticmethod
    def reshow_settings():
        FigureMaker._unhide_button = Button(label="<", width=40, height=40, css_classes=["other_button"])
        FigureMaker._unhide_button.sizing_mode = "fixed"
        FigureMaker._unhide_button.visible = False

        def event(e):
            FigureMaker.toggle_hide("tools")
        FigureMaker._unhide_button.on_click(event)
        return FigureMaker._unhide_button


class MainLayout:
    def dropdown_select_h(self, title, event, tooltip):

        ret = Dropdown(label=title, menu=[], width=SETTINGS_WIDTH, sizing_mode="fixed", 
                        css_classes=["other_button", "tooltip", tooltip], height=DROPDOWN_HEIGHT)

        options = []
        d = {}

        def make_menu():
            menu = []
            for name, key in options:
                menu.append((("☑ " if d[key] else "☐ ") + name, key))
            ret.menu = menu

        def set_menu(op):
            nonlocal options
            nonlocal d
            options = op
            d = {}
            for _, key in options:
                d[key] = False
            d[options[0][1]] = True
            make_menu()

        def _event(e):
            for _, key in options:
                d[key] = False
            d[e.item] = True
            event(e.item)
            make_menu()
            self.trigger_render()
        ret.on_click(_event)
        return ret, set_menu

    def dropdown_select(self, title, event, tooltip, *options):
        ret, set_menu = self.dropdown_select_h(title, event, tooltip)
        set_menu([*options])
        return ret

    def multi_choice(self, label):
        div = Div(text=label)
        #div.margin = DIV_MARGIN
        choice = MultiChoice(value=[], options=[])
        choice.on_change("value", lambda x, y, z: self.trigger_render())

        clear_button = Button(label="none", css_classes=["other_button"], width=50, sizing_mode="fixed")
        def clear_event(e):
            choice.value = []
        clear_button.on_click(clear_event)
        all_button = Button(label="all", css_classes=["other_button"], width=50, sizing_mode="fixed")
        def all_event(e):
            choice.value = [x for x, _ in choice.options]
        all_button.on_click(all_event)

        layout = column([row([
            div, clear_button, all_button
        ], sizing_mode="stretch_width"), choice], sizing_mode="stretch_width")

        return choice, layout

    def make_slider_spinner(self, title="", value=1, start=0, end=10, step=None, width=200, 
                            on_change=lambda _a,_b,_c: None, spinner_width=80, sizing_mode="stretch_width"):
        spinner = Spinner(value=value, low=start, high=end, step=step, width=spinner_width)
        slider = Slider(title=title, value=value, start=start, end=end, step=step, show_value=False, width=width-spinner_width, sizing_mode=sizing_mode)

        spinner.js_link("value", slider, "value")
        slider.js_link("value", spinner, "value")
        slider.on_change("value_throttled", on_change)
        spinner.on_change("value_throttled", on_change)

        return slider, row([slider, spinner], width=width)

    def make_range_slider_spinner(self, title="", value=(1, 2), start=0, end=10, step=None, width=200, 
                            on_change=lambda _a,_b,_c: None, spinner_width=80, sizing_mode="stretch_width"):
        slider = RangeSlider(title=title, value=value, start=start, end=end, step=step, show_value=False, width=width-spinner_width*2, sizing_mode=sizing_mode)
        spinner_start = Spinner(value=value[0], low=start, high=end, step=step, width=spinner_width)
        spinner_end = Spinner(value=value[1], low=start, high=end, step=step, width=spinner_width)

        spinner_start.js_on_change('value', CustomJS(args=dict(other=slider), code="other.value = [this.value, other.value[1]]" ) )
        slider.js_link("value", spinner_start, "value", attr_selector=0)

        spinner_end.js_on_change('value', CustomJS(args=dict(other=slider), code="other.value = [other.value[0], this.value]" ) )
        slider.js_link("value", spinner_end, "value", attr_selector=1)

        slider.on_change("value_throttled", on_change)
        spinner_end.on_change("value_throttled", on_change)
        spinner_start.on_change("value_throttled", on_change)

        return slider, row([slider, spinner_start, spinner_end], width=width)


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
        self.render_last_time = None
        self.render_time_record = []

        global SETTINGS_WIDTH
        tollbars = []
        self.heatmap = FigureMaker().range1d().stretch().combine_tools(tollbars).get()

        d = {"b": [], "l": [], "t": [], "r": [], "c": [], "chr_x": [], "chr_y": [], "x1": [], "x2": [],
             "y1": [], "y2": [], "s": [], "d_a": [], "d_b": [], 'info': []}
        self.heatmap_data = ColumnDataSource(data=d)
        self.heatmap.quad(left="l", bottom="b", right="r", top="t", fill_color="c", line_color=None,
                          source=self.heatmap_data, level="underlay")

        d = {"b": [], "l": [], "t": [], "r": []}
        self.overlay_data = ColumnDataSource(data=d)
        self.heatmap.quad(left="l", bottom="b", right="r", top="t", fill_color=None, line_color="red", 
                            source=self.overlay_data, level="underlay")

        self.overlay_dataset_id = Spinner(title="Overlay Lines Dataset Id", low=-1, step=1, value=-1, 
                                          width=DEFAULT_SIZE, mode="int")
        self.overlay_dataset_id.on_change("value_throttled", lambda x, y, z: self.trigger_render())


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

        FigureMaker._slope = Slope(gradient=1, y_intercept=0, line_color=None)
        self.heatmap.add_layout(FigureMaker._slope)

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
        #SETTINGS_WIDTH = tool_bar.width
        show_hide = FigureMaker.show_hide_dropdown(("Axes", "axis"), (RATIO_PLOT_NAME, "ratio"), (RAW_PLOT_NAME, "raw"),
                                                   (ANNOTATION_PLOT_NAME, "annotation"), ("Tools", "tools"))

        self.in_group_d = "sum"

        def in_group_event(e):
            self.in_group_d = e
            self.trigger_render()
        self.in_group = self.dropdown_select("In Group", in_group_event, "tooltip_in_group",
                                             ("Sum [a+b+c+...]", "sum"), 
                                             ("Minimium [min(a,b,c,...)]", "min"),
                                             ("Difference [|a-b|+|a-c|+|b-c|+...]", "dif"))

        self.betw_group_d = "sum"

        def betw_group_event(e):
            self.betw_group_d = e
            self.trigger_render()
        self.betw_group = self.dropdown_select("Between Group", betw_group_event, "tooltip_between_groups",
                                               ("Sum [a+b]", "sum"), ("Show First Group [a]", "1st"), (
                                                   "Show Second Group [b]", "2nd"), ("Substract [a-b]", "sub"),
                                               ("Difference [|a-b|]", "dif"), ("Minimum [min(a,b)]", "min"), ("Maximum [max(a,b)]", "max"))

        self.symmetrie_d = "all"

        def symmetrie_event(e):
            self.symmetrie_d = e
            self.trigger_render()
        self.symmetrie = self.dropdown_select("Symmetry", symmetrie_event, "tooltip_symmetry",
                                              ("Show All Interactions", "all"), 
                                              ("Only Show Symmetric Interactions", "sym"),
                                              ("Only Show Asymmetric Interactions", "asym"),
                                              ("Make Interactions Symmetric (Bottom to Top)", "topToBot"), 
                                              ("Make Interactions Symmetric (Top to Bottom)", "botToTop"))

        self.normalization_d = "max_bin_visible"

        def normalization_event(e):
            self.normalization_d = e
            self.trigger_render()
        self.normalization = self.dropdown_select("Normalize by", normalization_event, "tooltip_normalize_by",
                                                  ("Largest Rendered Bin",
                                                   "max_bin_visible"),
                                                  ("Reads per Million",
                                                   "rpm"), 
                                                  ("Reads per Thousand",
                                                   "rpk"), 
                                                   ("Column Sum", "column"),
                                                   ("Row Sum", "row"),
                                                  ("Coverage Track (Absolute)",
                                                   "tracks_abs"),
                                                  ("Coverage Track (Scaled)", "tracks_rel"),
                                                  ("Binominal Test", "radicl-seq"),
                                                  ("Iterative Correction", "hi-c"),
                                                  ("Distance Dependent Decay", "ddd"),
                                                  )

        self.square_bins_d = "view"
        def square_bin_event(e):
            self.square_bins_d = e
            self.trigger_render()
        square_bins = self.dropdown_select("Bin Aspect Ratio", square_bin_event, "tooltip_bin_aspect_ratio",
                                                  ("Squared relative to view",
                                                   "view"),
                                                  ("Squared relative to coordinates",
                                                   "coord")
                                                   )
        self.power_ten_bin_d = "p10"
        def power_ten_bin_event(e):
            self.power_ten_bin_d = e
            self.trigger_render()
        power_ten_bin = self.dropdown_select("Snap Bin Size", power_ten_bin_event, "tooltip_snap_bin_size",
                                                ("To Even Power of Ten", "p10"),
                                                ("Do not snap", "no")
                                            )

        self.color_d = "Viridis256"
        def color_event(e):
            self.color_d = e
            self.trigger_render()
        color_picker = self.dropdown_select("Color Palette", color_event, "tooltip_color",
                                                ("Viridis", "Viridis256"),
                                                ("Plasma", "Plasma256"),
                                                ("Turbo", "Turbo256"),
                                                ("Greys", "Greys256"),
                                                  )

        self.multi_mapping_d = "enclosed"
        def multi_mapping_event(e):
            self.multi_mapping_d = e
            self.trigger_render()
        multi_mapping = self.dropdown_select("Ambiguous Mapping", multi_mapping_event, "tooltip_multi_mapping",
                                                ("Count read if all mapping loci are within a bin", "enclosed"),
                                                ("Count read if mapping loci bounding-box overlaps bin", "overlaps"),
                                                ("Count read if first mapping loci is within a bin", "first"),
                                                ("Count read if last mapping loci is within a bin", "last"),
                                                ("Count read if there is only one mapping loci", "points_only"),
                                                  )

        def stretch_event(e):
            self.heatmap.sizing_mode = e
            if e == "stretch_both":
                self.settings.width_policy = "fixed"
            else:
                self.settings.width_policy = "max"
        self.stretch = self.dropdown_select("Stretch/Scale", stretch_event, "tooltip_stretch_scale",
                                                  ("Stretch", "stretch_both"),
                                                  ("Scale", "scale_height"))

        self.mapq_slider, ms_l = self.make_range_slider_spinner(width=SETTINGS_WIDTH, start=0, end=MAP_Q_MAX, 
                                        value=(0, MAP_Q_MAX), step=1,
                                       title="Mapping Quality Bounds", sizing_mode="stretch_width",
                                       on_change=lambda x, y, z: self.trigger_render())

        self.interactions_bounds_slider, ibs_l = self.make_slider_spinner(width=SETTINGS_WIDTH, start=0, end=100, 
                                                  value=0, step=1,
                                                 title="Minimum Interactions", 
                                                 on_change=lambda x, y, z: self.trigger_render(), sizing_mode="stretch_width")
        

        self.color_range_slider, crs_l = self.make_range_slider_spinner(width=SETTINGS_WIDTH, start=0, end=1, value=(0, 1), 
                                                step=0.01,
                                                 title="Color Scale Range", sizing_mode="stretch_width",
                                                 on_change=lambda x, y, z: self.trigger_render())

        self.interactions_slider, is_l = self.make_slider_spinner(width=SETTINGS_WIDTH, start=-50, end=50, value=10, step=0.1,
                                          title="Color Scale Log Base", 
                                          on_change=lambda x, y, z: self.trigger_render(),
                                          sizing_mode="stretch_width")  # , format="0[.]000")

        self.update_frequency_slider, ufs_l = self.make_slider_spinner(width=SETTINGS_WIDTH, start=0.1, end=3, value=0.5, 
                                               step=0.1,
                                              title="Update Frequency [seconds]" #, format="0[.]000"
                                              , sizing_mode="stretch_width")

        self.redraw_slider, rs_l = self.make_slider_spinner(width=SETTINGS_WIDTH, start=0, end=100, value=90, step=1,
                                    on_change=lambda x, y, z: self.trigger_render(),
                                    title="Redraw if zoomed in by [%]", sizing_mode="stretch_width")

        self.add_area_slider, aas_l = self.make_slider_spinner(width=SETTINGS_WIDTH, start=0, end=500, value=20, step=10,
                                      on_change=lambda x, y, z: self.trigger_render(),
                                      title="Additional Draw Area [%]", sizing_mode="stretch_width")

        self.diag_dist_slider, dds_l = self.make_slider_spinner(width=SETTINGS_WIDTH, start=0, end=1000,
                                       value=0, step=1,
                                       on_change=lambda x, y, z: self.trigger_render(),
                                       title="Minimum Distance from Diagonal (kbp)", sizing_mode="stretch_width")

        def anno_size_slider_event(attr, old, new):
            self.anno_x.width = self.anno_size_slider.value
            self.anno_x_axis.width = self.anno_size_slider.value
            self.anno_y.height = self.anno_size_slider.value
            self.anno_y_axis.height = self.anno_size_slider.value
        self.anno_size_slider, ass_l = self.make_slider_spinner(width=SETTINGS_WIDTH, start=10, end=500, 
                                       value=DEFAULT_SIZE,   step=1,
                                       title=ANNOTATION_PLOT_NAME + " Plot Size", sizing_mode="stretch_width",
                                       on_change=anno_size_slider_event)

        def ratio_size_slider_event(attr, old, new):
            self.ratio_x.width = self.ratio_size_slider.value
            self.ratio_x_axis.width = self.ratio_size_slider.value
            self.ratio_y.height = self.ratio_size_slider.value
            self.ratio_y_axis.height = self.ratio_size_slider.value
        self.ratio_size_slider, rss1_l = self.make_slider_spinner(width=SETTINGS_WIDTH, start=10, end=500, 
                                        value=DEFAULT_SIZE, step=1,
                                        title=RATIO_PLOT_NAME + " Plot Size", sizing_mode="stretch_width",
                                        on_change=ratio_size_slider_event)

        def raw_size_slider_event(attr, old, new):
            self.raw_x.width = self.raw_size_slider.value
            self.raw_x_axis.width = self.raw_size_slider.value
            self.raw_y.height = self.raw_size_slider.value
            self.raw_y_axis.height = self.raw_size_slider.value
        self.raw_size_slider, rss2_l = self.make_slider_spinner(width=SETTINGS_WIDTH, start=10, end=500, 
                                      value=DEFAULT_SIZE, step=1,
                                      title=RAW_PLOT_NAME + " Plot Size", sizing_mode="stretch_width",
                                      on_change=raw_size_slider_event)

        self.num_bins, nb_l = self.make_slider_spinner(width=SETTINGS_WIDTH, start=10, end=1000, value=50, step=10,
                               on_change=lambda x, y, z: self.trigger_render(),
                               title="Number of Bins (in thousands)", sizing_mode="stretch_width")

            
        self.radical_seq_accept, rsa_l = self.make_slider_spinner(width=SETTINGS_WIDTH, start=0.01, end=0.1, value=0.05, step=0.01,
                               title="pAccept for binominal test", sizing_mode="stretch_width",
                               on_change=lambda x, y, z: self.trigger_render())
            
        meta_file_label = Div(text="Data path:")
        meta_file_label.margin = DIV_MARGIN
        self.meta_file = TextInput(value="smoother_out/")
        self.meta_file.on_change("value", lambda x, y, z: self.setup())

        self.group_a, group_a_layout = self.multi_choice("Group A")
        self.group_b, group_b_layout = self.multi_choice("Group B")
        

        self.displayed_annos, displayed_annos_layout = self.multi_choice("Displayed Annotations:")
        
        self.filtered_annos_x, filtered_annos_x_layout = self.multi_choice("Filter rows that overlap with:")
        self.filtered_annos_y, filtered_annos_y_layout = self.multi_choice("Filter columns that overlap with:")

        power_tick = FuncTickFormatter(
            code="""
            if (tick / 9 >= 7)
                return Math.ceil((1 + tick % 9)) + "*10^" + Math.floor(tick / 9) + "bp";
            else if (tick / 9 >= 3)
                return Math.ceil((1 + tick % 9) * Math.pow(10, Math.floor(tick / 9)-3)) + "kbp";
            else
                return Math.ceil((1 + tick % 9) * Math.pow(10, Math.floor(tick / 9))) + "bp"; """)
        self.min_max_bin_size = RangeSlider(start=0, end=9*15, value=(9*2, 9*6), step=1, title="Bin Size Bounds [nt]",
                                            format=power_tick)
        self.min_max_bin_size.on_change(
            "value_throttled", lambda x, y, z: self.trigger_render())

        def callback(a, b):
            self.min_max_bin_size.value = (
                min(max(self.min_max_bin_size.value[0] + a, self.min_max_bin_size.start), self.min_max_bin_size.end), 
                min(max(self.min_max_bin_size.value[1] + b, self.min_max_bin_size.start), self.min_max_bin_size.end)) 
            self.trigger_render()
        button_s_up = Button(label="▲", button_type="light", width=15, height=15, margin=BTN_MARGIN)
        button_s_up.on_click(lambda _: callback(1, 0))
        button_s_down = Button(label="▼", button_type="light", width=15, height=15, margin=BTN_MARGIN)
        button_s_down.on_click(lambda _: callback(-1, 0))
        button_e_up = Button(label="▲", button_type="light", width=15, height=15, margin=BTN_MARGIN)
        button_e_up.on_click(lambda _: callback(0, 1))
        button_e_down = Button(label="▼", button_type="light", width=15, height=15, margin=BTN_MARGIN)
        button_e_down.on_click(lambda _: callback(0, -1))

        mmbs_l = row([self.min_max_bin_size, column([button_s_up, button_s_down]), column([button_e_up, button_e_down])])

        self.curr_bin_size = Div(text="Current Bin Size: n/a", sizing_mode="stretch_width")
        
        self.spinner = Div(text="<div class=\"lds-spinner\"><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div></div>")
        #self.spinner = Div(text="<div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div>", css_classes=["lds-spinner"])
        self.spinner.css_classes = ["fade-out"]

        self.info_field = row([self.spinner, self.curr_bin_size], css_classes=["twenty_percent"])
        self.info_field.height = 100
        self.info_field.min_height = 100
        self.info_field.height_policy = "fixed"

        self.norm_x, norm_x_layout = self.multi_choice("Normalization Rows:")
        self.norm_y, norm_y_layout = self.multi_choice("Normalization Columns:")

        def x_coords_event(e):
            FigureMaker.x_coords_d = e
            self.setup_coordinates()
            self.trigger_render()
        x_coords, self.x_coords_update = self.dropdown_select_h("Row Coordinates", x_coords_event,
                                                                 "tooltip_row_coordinates")

        def y_coords_event(e):
            FigureMaker.y_coords_d = e
            self.setup_coordinates()
            self.trigger_render()
        y_coords, self.y_coords_update = self.dropdown_select_h("Column Coordinates", y_coords_event,
                                                                 "tooltip_column_coordinates")

        
        self.chrom_x, chrom_x_layout = self.multi_choice("Row Chromosomes")
        self.chrom_y, chrom_y_layout = self.multi_choice("Column Chromosomes")

        self.multiple_anno_per_bin_d = "combine"
        def multiple_anno_per_bin_event(e):
            self.multiple_anno_per_bin_d = e
            self.trigger_render()
        multiple_anno_per_bin = self.dropdown_select("Multiple Annotations in Bin", multiple_anno_per_bin_event, 
                "tooltip_multiple_annotations_in_bin", 
                ("Combine region from first to last annotation", "combine"), 
                ("Use first annotation", "first"), 
                ("Use Random annotation", "random"), 
                ("Increase number of bins to match number of annotations (might be slow)", "force_separate"))

        self.do_export = None
        def export_event(e):
            self.do_export = e
            self.trigger_render()
        self.export_button = self.dropdown_select("Export", export_event, "tooltip_export",
                                                  ("Current View", "current"),
                                                  ("Full Matrix", "full"))

        export_label = Div(text="Output Prefix:")
        export_label.margin = DIV_MARGIN
        self.export_file = TextInput(value="export1")
        
        self.export_sele, export_sele_layout = self.multi_choice("Export Selection")
        self.export_sele.options = [
            ("heatmap", "Heatmap"),
            ("col_sum", "Column Sum"),
            ("row_sum", "Row Sum")
        ]
        self.export_sele.value = ["heatmap"]
    
        self.export_type, export_type_layout = self.multi_choice("Export Type")
        self.export_type.options = [
            ("data", "Data"),
            #("svg", "SVG-Picture"), # cannot find non buggy selenium version
            #("png", "PNG-Picture")
        ]
        self.export_type.value = ["data"]

        grid_seq_config = Button(label="Grid Seq-like @todo", sizing_mode="stretch_width", 
                                 css_classes=["other_button", "tooltip", "tooltip_grid_seq"],
                                 height=DROPDOWN_HEIGHT)
        def grid_seq_event(e):
            # @todo 
            self.normalization_d = "column"
            self.trigger_render()
        grid_seq_config.on_click(grid_seq_event)
        radicl_seq_config = Button(label="Radicl Seq-like", sizing_mode="stretch_width", 
                                   css_classes=["other_button", "tooltip", "tooltip_radicl_seq"],
                                   height=DROPDOWN_HEIGHT)
        def radicl_seq_event(e):
            self.normalization_d = "radicl-seq" # @todo also update menu
            self.betw_group_d = "max"
            self.trigger_render()
        radicl_seq_config.on_click(radicl_seq_event)

        def make_panel(title, tooltip, children):
            t = Toggle(active=title == "General", button_type="light", css_classes=["menu_group", "tooltip", tooltip],
                       height=DROPDOWN_HEIGHT)

            cx = column(children, sizing_mode="stretch_width", css_classes=["offset_left"])
            cx.margin = [0, 20, 0, 20]

            r = column([t, cx], sizing_mode="stretch_width")
            def callback(e):
                if t.active:
                    p = "▿ "
                else:
                    p = "▸ "
                t.label = p + title
                def set_visible(x):
                    if isinstance(x, Box):
                        for c in x.children:
                            set_visible(c)
                    else:
                        x.visible = t.active
                set_visible(cx)
            t.on_click(callback)
            callback(None)
            return r

        with open("smoother/VERSION", "r") as in_file:
            smoother_version = in_file.readlines()[0][:-1]

        version_info = Div(text="Smoother "+ smoother_version +"<br>LibSps Version: " + bin.libSps.VERSION)

        _settings = column([
                make_panel("General", "tooltip_general", [tool_bar, meta_file_label, self.meta_file]),
                make_panel("Normalization", "tooltip_normalization", [self.normalization, 
                                    ibs_l, crs_l, is_l, norm_x_layout, norm_y_layout, rsa_l]),
                make_panel("Replicates", "tooltip_replicates", [self.in_group, self.betw_group, group_a_layout, group_b_layout]),
                make_panel("Interface", "tooltip_interface", [nb_l,
                                    show_hide, mmbs_l,
                                    ufs_l, rs_l, aas_l, ass_l, rss1_l, rss2_l,
                                    self.stretch, square_bins, power_ten_bin, color_picker, self.overlay_dataset_id]),
                make_panel("Filters", "tooltip_filters", [ms_l, self.symmetrie, dds_l, 
                                          displayed_annos_layout, filtered_annos_x_layout,
                                          filtered_annos_y_layout,
                                          x_coords, y_coords, multiple_anno_per_bin, chrom_x_layout, chrom_y_layout,
                                          multi_mapping]),
                make_panel("Export", "tooltip_export", [export_label, self.export_file, export_sele_layout, 
                                        #export_type_layout, 
                                      self.export_button]),
                make_panel("Quick Config", "tooltip_quick_config", [grid_seq_config, radicl_seq_config]),
                make_panel("Info", "tooltip_info", [version_info]),
            ],
            sizing_mode="stretch_both",
            css_classes=["scroll_y"]
        )
        #_settings.height = 100
        #_settings.min_height = 100
        #_settings.height_policy = "fixed"


        _settings_n_info = column([
                self.info_field,
                _settings
            ],
            sizing_mode="fixed",
            css_classes=["full_height"]
        )
        _settings_n_info.width = SETTINGS_WIDTH
        _settings_n_info.width_policy = "fixed"
        

        FigureMaker._hidable_plots.append((_settings_n_info, ["tools"]))
        self.settings = row([Spacer(sizing_mode="stretch_both"), _settings_n_info, FigureMaker.reshow_settings()], css_classes=["full_height"])
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

    def bin_cols_or_rows(self, area, h_bin, base_idx=0, none_for_chr_border=False, filter_annos=[], chr_filter=None, 
                        anno_coords=None):
        ret = []
        ret_2 = []
        ret_3 = []
        if anno_coords is None:
            coords = self.meta.chr_sizes.bin_cols_or_rows(h_bin, area[base_idx], area[base_idx+2], none_for_chr_border, 
                                                            chr_filter, is_canceld=lambda: self.cancel_render)
            if self.normalization_d == "hi-c":
                # move start of first bin to start of genome
                coords[0][1 if none_for_chr_border else 0][1] += coords[0][1 if none_for_chr_border else 0][0]
                coords[0][1 if none_for_chr_border else 0][0] = 0
            
                # move end of last bin to end of genome
                coords[0][-2 if none_for_chr_border else -1][1] = \
                    self.meta.chr_sizes.chr_start_pos["end"] - coords[0][1 if none_for_chr_border else 0][0]

            if self.cancel_render:
                return
        else:
            coords = self.meta.annotations[anno_coords].bin_cols_or_rows(h_bin, self.meta.chr_sizes.chr_order,
                                                                        self.meta.chr_sizes.chr_starts,
                                                                         area[base_idx], area[base_idx+2], 
                                                                         none_for_chr_border, chr_filter,
                                                                         self.multiple_anno_per_bin_d, is_canceld=lambda: self.cancel_render)
            if self.cancel_render:
                return
        for pos_1, pos_2, pos_3 in zip(*coords):
            not_filtered = True
            if not pos_1 is None and len(filter_annos) > 0:
                p, s = pos_1
                for anno_name in filter_annos:
                    if self.meta.annotations[anno_name].count(p, p+s) > 0:
                        not_filtered = False
                        break
            if self.cancel_render:
                return
            if not_filtered:
                ret.append(pos_1)
                ret_2.append(pos_2)
                ret_3.append(pos_3)
        return ret, ret_2, ret_3

    def bin_cols(self, area, h_bin, none_for_chr_border=False, filter_l=None):
        if filter_l is None:
            filter_l = self.filtered_annos_y.value
        anno_coords = None
        if FigureMaker.x_coords_d != "full_genome":
            anno_coords = FigureMaker.x_coords_d
        return self.bin_cols_or_rows(area, h_bin, 0, none_for_chr_border, filter_l, self.chrom_x.value, anno_coords)

    def bin_rows(self, area, h_bin, none_for_chr_border=False, filter_l=None):
        if filter_l is None:
            filter_l = self.filtered_annos_x.value
        anno_coords = None
        if FigureMaker.y_coords_d != "full_genome":
            anno_coords = FigureMaker.y_coords_d
        return self.bin_cols_or_rows(area, h_bin, 1, none_for_chr_border, filter_l, self.chrom_y.value, anno_coords)

    def bin_coords(self, area, h_bin, w_bin):
        h_bin = max(1, h_bin)
        ret = []
        ret_2 = []
        ret_3 = []
        xx = self.bin_cols(area, h_bin)
        if self.cancel_render:
            return
        a, a_2, a_3 = xx
        xx = self.bin_rows(area, w_bin)
        if self.cancel_render:
            return
        b, b_2, b_3 = xx
        for (x, w), (x_chr, x_2), (x_3, w_3) in zip(a, a_2, a_3):
            for (y, h), (y_chr, y_2), (y_3, h_3) in zip(b, b_2, b_3):
                ret.append((x, y, w, h))
                ret_2.append((x_chr, x_2, y_chr, y_2))
                ret_3.append((x_3, y_3, w_3, h_3))
                if self.cancel_render:
                    return
        return ret, a, b, ret_2, a_2, b_2, ret_3, a_3, b_3

    def adjust_bin_pos_for_symmetrie(self, x, y, w, h):
        if self.symmetrie_d == "botToTop":
            if x >= y:
                return y, x, h, w
        if self.symmetrie_d == "topToBot":
            if y >= x:
                return y, x, h, w
        return x, y, w, h

    def make_bins(self, bin_coords, name="make_bins"):
        bins = []
        info = [""]*len(bin_coords)
        min_ = self.interactions_bounds_slider.value
        for idx, _ in sorted(list(self.meta.datasets.items())):
            bins.append([])
            for idx_2, (x, y, w, h) in enumerate(bin_coords):
                self.render_step_log(name, idx_2 + idx * len(bin_coords), len(bin_coords)*len(self.meta.datasets))
                if abs(x - y) >= 1000 * self.diag_dist_slider.value / self.meta.dividend:
                    x, y, w, h = self.adjust_bin_pos_for_symmetrie(x, y, w, h)
                    n = self.idx.count(idx, y, y+h, x, x+w, *self.mapq_slider.value,
                                       self.multi_mapping_d) # , min(h, w), min(h, w)
                    bins[-1].append(max(n-min_, 0))
                    if n <= 10:
                        info[idx_2] += self.idx.info(idx, y, y+h, x, x+w, *self.mapq_slider.value)
                else:
                    bins[-1].append(0)
                if self.cancel_render:
                    return
        return bins, info

    def col_norm(self, cols):
        x = self.make_bins([(c[0], 0, c[1], self.meta.chr_sizes.chr_start_pos["end"])
                                        if not c is None else (-2, -2, 1, 1) for c in cols], name="make_col_norm_bins")
        if self.cancel_render:
            return
        return self.flatten_bins(x[0])

    def row_norm(self, rows):
        x = self.make_bins([(0, c[0], self.meta.chr_sizes.chr_start_pos["end"], c[1])
                                        if not c is None else (-2, -2, 1, 1) for c in rows], name="make_row_norm_bins")
        if self.cancel_render:
            return
        return self.flatten_bins(x[0])

    def read_norm(self, idx):
        n = []
        for idx, dataset in sorted(list(self.meta.datasets.items())):
            if str(idx) in (self.group_a.value if idx == 0 else self.group_b.value):
                val = self.idx.count(idx, 0, self.meta.chr_sizes.chr_start_pos["end"], 0, 
                                     self.meta.chr_sizes.chr_start_pos["end"], *self.mapq_slider.value)
                n.append(val)
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
        if len((self.norm_x.value if rows else self.norm_y.value)) == 0:
            return 1
        return self.flatten_norm([
            [self.idx_norm.count(int(idx), 0, self.meta.chr_sizes.chr_start_pos["end"], *self.mapq_slider.value) \
                if self.meta.norm_via_tree(int(idx)) \
                else self.meta.norm[int(idx)].count(0, self.meta.chr_sizes.chr_start_pos["end"]) \
                for idx in (self.norm_x.value if rows else self.norm_y.value)]])[0]

    def hi_c_normalization(self, bins, cols, rows):
        # max 50 iterations
        for num_itr in range(50): 
            assert len(bins) == len(cols) * len(rows)
            # compute coverage & width
            cov_rows = [(sum(bins[y + len(cols) * x] for y in range(len(cols))), v[1]) for x, v in enumerate(rows)]
            cov_cols = [(sum(bins[y + len(cols) * x] for x in range(len(rows))), v[1]) for y, v in enumerate(cols)]
            def unit_mean(l):
                total_width = sum(w for v, w in l if v > 0)
                cnt = 0
                m = 1
                for m, w in sorted([(v, w) for v, w in l if v > 0]):
                    if cnt + w > total_width / 2:
                        break
                    cnt += w
                return [r if r != 0 else 1 for r in [x / m for x, _ in l]]

            cov_cols = unit_mean(cov_cols)
            cov_rows = unit_mean(cov_rows)
            assert len(cov_cols) == len(cols)
            assert len(cov_rows) == len(rows)
            assert len(bins) == len(cov_cols) * len(cov_rows)

            max_bias_delta = 0
            for idx in range(len(bins)):
                bias_delta = cov_cols[idx % len(cols)] * cov_rows[idx // len(cols)]
                bins[idx] = bins[idx] / bias_delta
                max_bias_delta = max(max_bias_delta, abs(1-bias_delta))

            if max_bias_delta < 0.01:
                print("stopped at iteration", num_itr, "since max_bias_delta is", max_bias_delta)
                break
        
        n = max(bins + [1])
        return [x/n for x in bins]


    def norm_bins(self, w_bin, bins_l, cols, rows):
        ret = []
        if self.normalization_d in ["tracks_abs", "tracks_rel"]:
            raw_x_norm = self.linear_bins_norm(rows, True)
            if self.cancel_render:
                return
            raw_x_norm = raw_x_norm[0]
            raw_y_norm = self.linear_bins_norm(cols, False)
            if self.cancel_render:
                return
            raw_y_norm = raw_y_norm[0]
        if self.normalization_d in ["column"]:
            ns = self.col_norm(cols)
        if self.normalization_d in ["row", "radicl-seq"]:
            ns = self.row_norm(rows)
        if self.cancel_render:
            return
        for idx, bins in enumerate(bins_l):
            if self.normalization_d != "ddd":
                self.render_step_log("norm_bins", idx, len(bins_l))
            if self.normalization_d == "max_bin_visible":
                n = max(bins + [1])
                ret.append([x/n for x in bins])
            elif self.normalization_d == "rpm":
                n = self.read_norm(idx)
                ret.append([1000000 * x/n for x in bins])
            elif self.normalization_d == "rpk":
                n = self.read_norm(idx)
                ret.append([1000 * x/n for x in bins])
            elif self.normalization_d == "column":
                ret.append([x / max(ns[idx][idx_2 // len(rows)], 1) for idx_2, x in enumerate(bins)])
            elif self.normalization_d == "row":
                ret.append([x / max(ns[idx][idx_2 % len(rows)], 1) for idx_2, x in enumerate(bins)])
            elif self.normalization_d == "radicl-seq":
                ret.append([0]*(len(rows)*len(cols)))
                for idx_2 in range(len(rows)):
                    row = bins[idx_2::len(rows)]
                    for idx_3, v in enumerate(radicl_seq_norm(row, ns[idx][idx_2], w_bin, 
                                                   self.meta.chr_sizes.chr_start_pos["end"],
                                                   self.radical_seq_accept.value)):
                        ret[-1][idx_2 + idx_3 * len(rows)] = v
            elif self.normalization_d in ["tracks_abs", "tracks_rel"]:
                n = self.read_norm(idx)

                def get_norm(i):
                    d = (raw_y_norm[i // len(rows)] * raw_x_norm[i % len(rows)] * n)
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
            elif self.normalization_d == "hi-c":
                ret.append(self.hi_c_normalization(bins, rows, cols))
            elif self.normalization_d == "ddd":
                # get the distances to sample
                dists_to_sample = set([(int(x)-int(y), w, h) for x, w in cols for y, h in rows])
                ddd = {}
                # for each distance we have to sample
                for id_2, (d, w, h) in enumerate(dists_to_sample):
                    self.render_step_log("norm_bins", id_2 + idx*len(dists_to_sample), len(bins_l)*len(dists_to_sample))
                    # sample until the result does not change anymore (less than 1%) but at least a 250 times
                    cnt = 0
                    val = 0
                    while True:
                        inc = 0
                        STEP_SIZE=10
                        for _ in range(STEP_SIZE):
                            if self.cancel_render:
                                return
                            s = int(max(0, d))
                            e = int(self.meta.chr_sizes.chr_start_pos["end"] - w - min(0, d))
                            if s == e:
                                x = s
                            else:
                                x = random.randrange(s, e, max(int(w), 1))
                            y = x-d
                            x_2, y_2, w_2, h_2 = self.adjust_bin_pos_for_symmetrie(x, y, w, h)
                            inc += self.idx.count(idx, y_2, y_2+h_2, x_2, x_2+w_2, *self.mapq_slider.value, 
                                                  self.multi_mapping_d)
                        if val > 0:
                            change = abs( (val/cnt) - ( (val+inc) / (cnt+STEP_SIZE) ) ) / (val/cnt)
                        else:
                            change = 1
                        if (cnt >= 50 and change < 0.02) or cnt > 500:
                            break
                        val += inc
                        cnt += STEP_SIZE
                    #print("d:", d, ", sampling took", cnt, "many attempts. Last change:", change)
                    ddd[d] = max(val/cnt, 1)
                
                to_append = [x / ddd[int(cols[idx_2 // len(rows)][0]) - int(rows[idx_2 % len(rows)][0])] for idx_2, x in enumerate(bins)]
                n = max(to_append + [1])
                ret.append([x/n for x in to_append])
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
        c = math.log(  a*( min(1,c)*( 1 - (1/a) ) + (1/a) )  ) / math.log(a)
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

    def color(self, x):
        if self.color_d == "Viridis256":
            return Viridis256[x]
        if self.color_d == "Plasma256":
            return Plasma256[x]
        if self.color_d == "Turbo256":
            return Turbo256[x]
        if self.color_d == "Greys256":
            return Greys256[x]
        return Viridis256[x]

    def color_range(self, c):
        c = (c - self.color_range_slider.value[0]) / (self.color_range_slider.value[1] - self.color_range_slider.value[0])
        return max(0, min(MAP_Q_MAX-1, int((MAP_Q_MAX-1)*c)))
        #color_range_slider

    def color_bins_b(self, bins):
        ret = []
        for c in bins:
            if self.betw_group_d == "sub":
                c = self.log_scale(abs(c)) * (1 if c >= 0 else -1) / 2 + 0.5
                c = self.color_range(c) 
                ret.append(self.color(c))
            else:
                if math.isnan(self.log_scale(c)):
                    ret.append(self.color(0))
                else:
                    ret.append(self.color(self.color_range(self.log_scale(c))))
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
            x = self.make_bins([(y, x, h, w) for x, y, w, h in bin_coords], name="make_bins_symmetrie")
            if self.cancel_render:
                return
            bins_2, _ = x
            norms = self.norm_bins(h_bin, bins_2, bin_rows, bin_cols)
            if self.cancel_render:
                return
            if self.symmetrie_d == "sym":
                return [[min(a, b) for a, b in zip(bin, norm)] for bin, norm in zip(bins, norms)]
            else:
                return [[max(a-b, 0) for a, b in zip(bin, norm)] for bin, norm in zip(bins, norms)]
        else:
            return bins

    def annotation_bins(self, bins, coverage_obj):
        return [coverage_obj.count(x[0], x[0] + x[1]) if not x is None else float('NaN') for x in bins]

    def linear_bins_norm(self, bins, rows):
        vals = []
        idxs = (self.norm_x.value if rows else self.norm_y.value)
        for x in bins:
            vals.append([])
            if len(idxs) == 0:
                vals[-1].append(1)
            else:
                for idx in idxs:
                    if x is None:
                        vals[-1].append(float('NaN'))
                    else:
                        if self.meta.norm_via_tree(int(idx)):
                            vals[-1].append(self.idx_norm.count(int(idx), x[0], x[0] + x[1], *self.mapq_slider.value))
                        else:
                            vals[-1].append(self.meta.norm[int(idx)].count(x[0], x[0] + x[1]))
                    if self.cancel_render:
                        return
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
        if self.render_last_time is None or (datetime.now() - self.render_last_time).seconds >= 1:
            self.render_last_time = datetime.now()
            s = "rendering due to " + self.render_reason + "."
            if len(step_name) > 0:
                s += " Step " + str(self.render_curr_step) + \
                    " " + str(step_name) + ". Substep " + str(sub_step)
                if not sub_step_total is None:
                    s += " of " + str(sub_step_total) + " = " + str((100*sub_step)//sub_step_total) + "%. "
                if len(self.render_time_record) > 0:
                    s += " Runtime: " + str(datetime.now() - self.render_time_record[-1][1])
                if self.cancel_render:
                    s += " CANCELLED!!"
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
        ram_usage = psutil.virtual_memory().percent
        print("Currently used RAM:", ram_usage, "%\033[K")
        print("Number of displayed bins:", bin_amount, "\033[K")
        return total_time, ram_usage


    @gen.coroutine
    @without_document_lock
    def render(self, area):
        def unlocked_task():
            def cancelable_task():
                self.cancel_render = False
                if self.meta is None or self.idx is None:
                    def callback():
                        self.curr_bin_size.text = "Waiting for Fileinput."
                    self.curdoc.add_next_tick_callback(callback)
                    self.curdoc.add_timeout_callback(
                        lambda: self.render_callback(), self.update_frequency_slider.value*1000)
                    return False
                    
                def callback():
                    self.spinner.css_classes = ["fade-in"]
                self.curdoc.add_next_tick_callback(callback)

                def power_of_ten(x):
                    if self.power_ten_bin_d == "no":
                        return math.ceil(x)
                    n = 0
                    while True:
                        for i in [1, 1.25, 2.5, 5]:
                            if i*10**n > x:
                                return i*10**n
                        n += 1
                def comp_bin_size(idx):
                    t = self.min_max_bin_size.value[idx]
                    return max(1, math.ceil((1 + t % 9) * 10**(t // 9)) // self.meta.dividend)
                if self.square_bins_d == "view":
                    h_bin = power_of_ten( (area[2] - area[0]) / math.sqrt(self.num_bins.value * 1000) )
                    h_bin = min(max(h_bin, comp_bin_size(0), 1), comp_bin_size(1))
                    w_bin = power_of_ten( (area[3] - area[1]) / math.sqrt(self.num_bins.value * 1000) )
                    w_bin = min(max(w_bin, comp_bin_size(0), 1), comp_bin_size(1))
                elif self.square_bins_d == "coord":
                    area_bin = (area[2] - area[0]) * (area[3] - area[1]) / (self.num_bins.value * 1000)
                    h_bin = power_of_ten(math.sqrt(area_bin))
                    h_bin = min(max(h_bin, comp_bin_size(0), 1), comp_bin_size(1))
                    w_bin = h_bin
                else:
                    raise RuntimeError("invlaid square_bins_d value")

                area[0] -= area[0] % w_bin # align to nice and even number
                area[1] -= area[1] % h_bin # align to nice and even number
                area[2] += w_bin - (area[2] % w_bin) # align to nice and even number
                area[3] += h_bin - (area[3] % h_bin) # align to nice and even number

                if self.do_export == "full":
                    area[0] = 0
                    area[1] = 0
                    area[2] = self.meta.chr_sizes.chr_start_pos["end"]
                    area[3] = self.meta.chr_sizes.chr_start_pos["end"]

                xx = self.bin_coords(area, h_bin, w_bin)
                if self.cancel_render:
                    return
                bin_coords, bin_cols, bin_rows, bin_coords_2, _, _, bin_coords_3, _, _ = xx
                print("bin_size", int(h_bin), "x", int(w_bin), "\033[K")
                xx = self.make_bins(bin_coords)
                if self.cancel_render:
                    return
                bins, info = xx
                flat = self.flatten_bins(bins)
                norm = self.norm_bins(w_bin, flat, bin_cols, bin_rows)
                if self.cancel_render:
                    return
                sym = self.bin_symmentry(h_bin, norm, bin_coords, bin_cols, bin_rows)
                if self.cancel_render:
                    return
                c = self.color_bins(sym)
                b_col = self.color((MAP_Q_MAX-1) //
                                2) if self.betw_group_d == "sub" else self.color(0)
                purged, purged_coords, purged_coords_2, purged_sym, purged_flat_a, purged_flat_b, purged_info = \
                    self.purge(b_col, c, bin_coords_3, bin_coords_2,
                            self.color_bins_a(sym), *flat, info)

                norm_visible = FigureMaker.is_visible("raw") or FigureMaker.is_visible("ratio")

                if norm_visible:
                    xx = self.bin_rows(area, w_bin, False)
                    if self.cancel_render:
                        return
                    raw_bin_rows, raw_bin_rows_2, raw_bin_rows_3 = xx
                    xx = self.bin_cols(area, h_bin, False)
                    if self.cancel_render:
                        return
                    raw_bin_cols, raw_bin_cols_2, raw_bin_cols_3 = xx

                    xx = self.linear_bins_norm(raw_bin_rows, True)
                    if self.cancel_render:
                        return
                    raw_x_norm_combined, raw_x_norms = xx

                    xx = self.linear_bins_norm(raw_bin_cols, False)
                    if self.cancel_render:
                        return
                    raw_y_norm_combined, raw_y_norms = xx

                    xx_raw_x_heat = self.row_norm(raw_bin_rows)
                    if self.cancel_render:
                        return
                    xx_raw_y_heat = self.col_norm(raw_bin_cols)
                    if self.cancel_render:
                        return
                    raw_x_heat = self.color_bins_a(xx_raw_x_heat)
                    raw_y_heat = self.color_bins_a(xx_raw_y_heat)
                    raw_x_ratio = [a/b if not b == 0 else 0 for a,
                                b in zip(raw_x_heat, raw_x_norm_combined)]
                    raw_y_ratio = [a/b if not b == 0 else 0 for a,
                                b in zip(raw_y_heat, raw_y_norm_combined)]
                else:
                    raw_bin_rows, raw_bin_rows_2, raw_bin_rows_3 = ([], [], [])
                    raw_bin_cols, raw_bin_cols_2, raw_bin_cols_3 = ([], [], [])

                    raw_x_norm_combined = []
                    raw_x_norms = [[]]
                    raw_y_norm_combined = []
                    raw_y_norms = [[]]
                    raw_x_heat = []
                    raw_y_heat = []
                    raw_x_ratio = []
                    raw_y_ratio = []
                    
                self.render_step_log("render_overlays")
                d_overlay = {"b": [], "l": [], "t": [], "r": []}
                if self.overlay_dataset_id.value >= 0:
                    for grid_pos, blf, trb in self.idx.get_overlay_grid(self.overlay_dataset_id.value):
                        if grid_pos[2] != 0:
                            continue
                        if grid_pos[3] != 0:
                            continue
                        if grid_pos[4] != 0:
                            continue
                        d_overlay["l"].append(min(blf[0], self.meta.chr_sizes.chr_start_pos["end"]))
                        d_overlay["b"].append(min(blf[1], self.meta.chr_sizes.chr_start_pos["end"]))
                        d_overlay["r"].append(min(trb[0], self.meta.chr_sizes.chr_start_pos["end"]))
                        d_overlay["t"].append(min(trb[1], self.meta.chr_sizes.chr_start_pos["end"]))

                self.render_step_log("setup_col_data_sources")
                d_heatmap = {
                    "b": [x[1] for x in purged_coords],
                    "l": [x[0] for x in purged_coords],
                    "t": [x[1] + x[3] for x in purged_coords],
                    "r": [x[0] + x[2] for x in purged_coords],
                    "c": purged,
                    "chr_x": [x[0] for x in purged_coords_2],
                    "chr_y": [x[2] for x in purged_coords_2],
                    "x1": [x[1] * self.meta.dividend for x in purged_coords_2],
                    "x2": [(x[1] + y[2]) * self.meta.dividend for x, y in zip(purged_coords_2, purged_coords)],
                    "y1": [x[3] * self.meta.dividend for x in purged_coords_2],
                    "y2": [(x[3] + y[3]) * self.meta.dividend for x, y in zip(purged_coords_2, purged_coords)],
                    "s": purged_sym,
                    "d_a": purged_flat_a,
                    "d_b": purged_flat_b,
                    "info": [x for x in purged_info],
                }
                

                def double_up(l):
                    return [x for x in l for _ in [0, 1]]

                x_pos = [p for x in raw_bin_rows_3 for p in [x[0], x[0] + x[1]]]
                x_chr = [x[0] for x in raw_bin_rows_2 for _ in [0, 1]]
                x_pos1 = [x[1] * self.meta.dividend for x in raw_bin_rows_2 for _ in [0, 1]]
                x_pos2 = [(x[1] + y[1]) * self.meta.dividend for x, y in zip(raw_bin_rows_2, raw_bin_rows) for _ in [0, 1]]

                x_num_raw = 2 + (0 if len(raw_x_norms) == 0 else len(raw_x_norms[0]))

                y_pos = [p for x in raw_bin_cols_3 for p in [x[0], x[0] + x[1]]]
                y_chr = [x[0] for x in raw_bin_cols_2 for _ in [0, 1]]
                y_pos1 = [x[1] * self.meta.dividend for x in raw_bin_cols_2 for _ in [0, 1]]
                y_pos2 = [(x[1] + y[1]) * self.meta.dividend for x, y in zip(raw_bin_cols_2, raw_bin_cols) for _ in [0, 1]]

                y_num_raw = 2 + (0 if len(raw_y_norms) == 0 else len(raw_y_norms[0]))

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
                
                ls_x = []
                if len(x_ys) > 0:
                    ls_x = [self.meta.normalizations[int(idx)][0] for idx in self.norm_x.value]
                ls_y = []
                if len(y_ys) > 0:
                    ls_y = [self.meta.normalizations[int(idx)][0] for idx in self.norm_y.value]

                raw_data_x = {
                    "xs": [x_pos for _ in range(x_num_raw)],
                    "chr": [x_chr for _ in range(x_num_raw)],
                    "pos1": [x_pos1 for _ in range(x_num_raw)],
                    "pos2": [x_pos2 for _ in range(x_num_raw)],
                    "ys": [double_up(raw_x_heat), double_up(raw_x_norm_combined)] + x_ys,
                    "ls": ["heatmap row sum", "combined"] + ls_x,
                    "cs": [Colorblind[8][idx % 8] for idx in range(x_num_raw)],
                }
                raw_data_y = {
                    "xs": [y_pos for _ in range(y_num_raw)],
                    "chr": [y_chr for _ in range(y_num_raw)],
                    "pos1": [y_pos1 for _ in range(y_num_raw)],
                    "pos2": [y_pos2 for _ in range(y_num_raw)],
                    "ys": [double_up(raw_y_heat), double_up(raw_y_norm_combined)] + y_ys,
                    "ls": ["heatmap col sum", "combined"] + ls_y,
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
                    bin_rows_unfiltr, bin_rows_2_unfiltr, bin_rows_3_unfiltr = self.bin_rows(area, w_bin, filter_l=[])
                    for idx, anno in enumerate(self.displayed_annos.value):
                        for rb_2, (s, e), x in zip(bin_rows_2_unfiltr, bin_rows_3_unfiltr,
                                                self.annotation_bins(bin_rows_unfiltr, self.meta.annotations[anno])):
                            if x > 0:
                                d_anno_x["chr"].append(rb_2[0])
                                d_anno_x["pos1"].append(rb_2[1] * self.meta.dividend)
                                d_anno_x["pos2"].append((rb_2[1] + e) * self.meta.dividend)
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
                    bin_cols_unfiltr, bin_cols_2_unfiltr, bin_cols_3_unfiltr = self.bin_cols(area, h_bin, filter_l=[])
                    for idx, anno in enumerate(self.displayed_annos.value):
                        for rb_2, (s, e), x in zip(bin_cols_2_unfiltr, bin_cols_3_unfiltr,
                                                self.annotation_bins(bin_cols_unfiltr, self.meta.annotations[anno])):
                            if x > 0:
                                d_anno_y["chr"].append(rb_2[0])
                                d_anno_y["pos1"].append(rb_2[1] * self.meta.dividend)
                                d_anno_y["pos2"].append((rb_2[1] + e) * self.meta.dividend)
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

                @gen.coroutine
                def callback():
                    self.curdoc.hold()
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
                    if self.do_export is None:
                        if len(self.displayed_annos.value) == 0:
                            self.anno_x.x_range.factors = [""]
                            self.anno_y.y_range.factors = [""]
                        else:
                            self.anno_x.x_range.factors = self.displayed_annos.value
                            self.anno_y.y_range.factors = self.displayed_annos.value

                    def readable_display(l):
                        l = l * self.meta.dividend
                        exp = int(math.log10(l)-1)
                        x = max(1, int(l / (10**exp)))
                        if exp >= 7:
                            return str(x) + "*10^" + str(exp) + "bp"
                        elif exp >= 3:
                            return str(x * int(10**(exp-3))) + "kbp"
                        else:
                            return str(x * int(10**exp)) + "bp"

                    end_text = "Rendering Done.<br>Current Bin Size: " + readable_display(w_bin) + \
                                            " x " + readable_display(h_bin) + "."


                    if self.do_export is None:
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
                        self.overlay_data.data = d_overlay
                    self.do_export = None
                    self.curdoc.unhold()
                    total_time, ram_usage = self.render_done(len(bins[0]))
                    self.curr_bin_size.text = end_text + "<br>Took " + str(total_time) + " in total.<br>" + str(ram_usage) + "% RAM used.<br> " + str(len(bins[0])//1000) + "k bins rendered."
                    self.curdoc.add_timeout_callback(
                        lambda: self.render_callback(), self.update_frequency_slider.value*1000)

                if not self.do_export is None:
                    if "data" in self.export_type.value:
                        if "heatmap" in self.export_sele.value:
                            with open(self.export_file.value + ".heatmap.bed", "w") as out_file:
                                for c, (x_chr_, x_2_, y_chr_, y_2_) in zip(self.color_bins_a(sym), bin_coords_2):
                                    out_file.write("\t".join([x_chr_, str(int(x_2_)), y_chr_, str(int(y_2_)), 
                                                            str(c)]) + "\n")
                        if "col_sum" in self.export_sele.value:
                            with open(self.export_file.value + ".columns.bed", "w") as out_file:
                                for c, x_chr_, x_2_, x_ in zip(raw_y_ratio, y_chr, y_pos1, y_pos):
                                    if not x_ is float('NaN'):
                                        out_file.write("\t".join([x_chr_, str(int(x_2_)), str(c)]) + "\n")
                        if "row_sum" in self.export_sele.value:
                            with open(self.export_file.value + ".rows.bed", "w") as out_file:
                                for c, x_chr_, x_2_, x_ in zip(raw_x_ratio, x_chr, x_pos1, x_pos):
                                    if not x_ is float('NaN'):
                                        out_file.write("\t".join([x_chr_, str(int(x_2_)), str(c)]) + "\n")
                    if "png" in self.export_type.value:
                        export_png(self.heatmap, filename=self.export_file.value + ".heatmap.png")
                    if "svg" in self.export_type.value:
                        bckup = self.heatmap.output_backend
                        self.heatmap.output_backend = "svg"
                        export_svg(self.heatmap, filename=self.export_file.value + ".heatmap.svg")
                        self.heatmap.output_backend = bckup

                self.curdoc.add_next_tick_callback(callback)
                return True
            while cancelable_task() is None:
                pass
            def callback():
                self.spinner.css_classes = ["fade-out"]
            self.curdoc.add_next_tick_callback(callback)

        yield executor.submit(unlocked_task)

    def setup_coordinates(self):
        self.meta.setup_coordinates(self, FigureMaker._show_hide["grid_lines"], FigureMaker.x_coords_d, 
                                    FigureMaker.y_coords_d)

    def setup(self):
        print("loading index...\033[K")
        self.spinner.css_classes = ["fade-in"]
        def callback():
            self.curr_bin_size.text = "loading index..."
            def callback2():
                if os.path.exists(self.meta_file.value + ".smoother_index"):
                    self.meta = MetaData.load(self.meta_file.value + ".smoother_index/meta")
                    self.meta.setup(self)
                    def to_idx(x):
                        if x <= 0:
                            return 0
                        power = int(math.log10(x))
                        return 9*power+math.ceil(x / 10**power)-1
                    self.min_max_bin_size.start = to_idx(self.meta.dividend)
                    self.min_max_bin_size.value = (max(9*2, to_idx(self.meta.dividend)), 9*6)
                    self.setup_coordinates()
                    self.idx = Tree_4(self.meta_file.value)
                    print("number of points in index: ", len(self.idx.index))
                    self.idx_norm = Tree_3(self.meta_file.value)
                    print("done loading\033[K")
                    self.trigger_render()
                    self.curr_bin_size.text = "done loading"
                else:
                    print("File not found")
                    self.curr_bin_size.text = "File not found"
            self.curdoc.add_next_tick_callback(callback2)
        self.curdoc.add_next_tick_callback(callback)

    def trigger_render(self):
        self.cancel_render = True
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
        self.curdoc.title = "Smoother"
        self.do_render = True
        self.force_render = True

        self.render_callback()
