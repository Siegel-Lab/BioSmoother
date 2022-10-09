__author__ = "Markus Schmidt"
__version__ = "0.0.3"
__email__ = "Markus.Schmidt@lmu.de"

from bokeh.layouts import grid, row, column
from bokeh.plotting import figure, curdoc
from bokeh.models.tools import ToolbarBox, ProxyToolbar
from bokeh.models import ColumnDataSource, Dropdown, Button, RangeSlider, Slider, TextInput, FuncTickFormatter, Div, HoverTool, Toggle, Box, Spinner, MultiSelect, CheckboxGroup, CrosshairTool, ColorPicker
#from bin.unsorted_multi_choice import UnsortedMultiChoice as MultiChoice
from bokeh.io import export_png, export_svg
import math
from datetime import datetime
from tornado import gen
from bokeh.document import without_document_lock
from bokeh.models import Panel, Tabs, Spacer, Slope, PreText, CustomJS, FixedTicker
from bokeh.models import Range1d, ColorBar, LinearColorMapper
from bin.meta_data import *
import os
import sys
from bin.heatmap_as_r_tree import *
from bokeh.palettes import Viridis256, Colorblind, Plasma256, Turbo256
from datetime import datetime, timedelta
import psutil
from concurrent.futures import ThreadPoolExecutor
from bokeh.models import BoxAnnotation
from bin.stats import *
from bokeh.models.tickers import AdaptiveTicker
import bin.libSps
from bin.render_step_logger import *
import json

SETTINGS_WIDTH = 400
DEFAULT_SIZE = 50
DROPDOWN_HEIGHT=30
ANNOTATION_PLOT_NAME = "Annotation"
RATIO_PLOT_NAME = "Ratio"
RAW_PLOT_NAME = "Cov"

DIV_MARGIN = (5, 5, 0, 5)
BTN_MARGIN = (3, 3, 3, 3)
BTN_MARGIN_2 = (3, 3, 3, 3)

CONFIG_FILE_VERSION = 0.1

executor = ThreadPoolExecutor(max_workers=1)

Colorblind2 = tuple(Colorblind[8][idx] for idx in [0,1,5,3,4,2,6,7])

class FigureMaker:
    _show_hide = {"grid_lines": False, "contig_borders": True, "indent_line": False}
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
        self.is_hidden = False

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
        if self.is_hidden:
            ret.visible = False
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

    def scale(self):
        self.args["sizing_mode"] = "scale_height"
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

    def x_axis_of(self, other, label="", stretch=False):
        self._axis_of(other)

        self.x_axis_visible = True
        self.args["x_range"] = other.x_range
        self.args["frame_height"] = 1
        if stretch:
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

    def y_axis_of(self, other, label="", stretch=False):
        self._axis_of(other)

        self.y_axis_visible = True
        self.args["y_range"] = other.y_range
        self.args["frame_width"] = 1
        if stretch:
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

    def hidden(self):
        self.is_hidden = True
        return self

    def hide_on(self, key):
        if not key in FigureMaker._show_hide:
            FigureMaker._show_hide[key] = not self.is_hidden
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
        cx = "lightgrey" if FigureMaker._show_hide["contig_borders"] else None
        cx2 = "lightgrey" if FigureMaker._show_hide["grid_lines"] else None
        cy = "lightgrey" if FigureMaker._show_hide["contig_borders"] else None
        cy2 = "lightgrey" if FigureMaker._show_hide["grid_lines"] else None
        FigureMaker._slope.line_color = "darkgrey" if FigureMaker._show_hide["indent_line"] else None
        for plot in FigureMaker._plots:
            if plot.xgrid.grid_line_color != cx:
                plot.xgrid.grid_line_color = cx
            if plot.xgrid.minor_grid_line_color != cx2:
                plot.xgrid.minor_grid_line_color = cx2
            if plot.ygrid.grid_line_color != cy:
                plot.ygrid.grid_line_color = cy
            if plot.ygrid.minor_grid_line_color != cy2:
                plot.ygrid.minor_grid_line_color = cy2

    @staticmethod
    def toggle_hide(key):
        FigureMaker._show_hide[key] = not FigureMaker._show_hide[key]
        FigureMaker.update_visibility()

    @staticmethod
    def is_visible(key):
        return FigureMaker._show_hide[key]

    @staticmethod
    def show_hide_dropdown(settings, *names):
        for _, key in names:
            if key not in FigureMaker._show_hide:
                FigureMaker._show_hide[key] = False
        for key in FigureMaker._show_hide.keys():
            FigureMaker._show_hide[key] = settings[key]
        FigureMaker.update_visibility()

        def make_menu():
            menu = []
            for name, key in names:
                menu.append(
                    (("☑ " if FigureMaker._show_hide[key] or key == "tools" else "☐ ") + name, key))
            menu.append(
                (("☑ " if FigureMaker._show_hide["grid_lines"] else "☐ ") + "Grid Lines", "grid_lines"))
            menu.append(
                (("☑ " if FigureMaker._show_hide["indent_line"] else "☐ ") + "Identity Line", "indent_line"))
            menu.append(
                (("☑ " if FigureMaker._show_hide["contig_borders"] else "☐ ") + "Contig Borders", "contig_borders"))
            return menu
        ret = Dropdown(label="Show/Hide", menu=make_menu(),
                       width=350, sizing_mode="fixed", css_classes=["other_button", "tooltip", "tooltip_show_hide"], height=DROPDOWN_HEIGHT)

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

        ret = Dropdown(label=title, menu=[], width=350, sizing_mode="fixed", 
                        css_classes=["other_button", "tooltip", tooltip], height=DROPDOWN_HEIGHT)

        options = []
        d = {}

        def make_menu():
            menu = []
            for name, key in options:
                menu.append((("● " if d[key] else "○ ") + name, key))
            ret.menu = menu

        def set_menu(op, active_item=None):
            nonlocal options
            nonlocal d
            options = op
            d = {}
            for _, key in options:
                d[key] = key == active_item
            if active_item is None:
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

    def dropdown_select(self, title, event, tooltip, *options, active_item=None):
        ret, set_menu = self.dropdown_select_h(title, event, tooltip)
        set_menu([*options], active_item)
        return ret

    def multi_choice(self, label, checkboxes, callback, orderable=True):
        div = Div(text=label)
        SYM_WIDTH = 10
        SYM_CSS = ["other_button"]
        CHECK_WIDTH = 20*len(checkboxes)
        ELEMENTS_PER_PAGE = 10

        col = column([], sizing_mode="stretch_width")
        #col.max_height=150
        empty = Div(text="", sizing_mode="fixed", width=30)
        
        spinner = TextInput(value="1", width=50, sizing_mode="fixed", visible=False)
        next_page = Button(label="", css_classes=SYM_CSS + ["fa_page_next_solid"], width=SYM_WIDTH, 
                                      sizing_mode="fixed", button_type="light", visible=False)
        prev_page = Button(label="", css_classes=SYM_CSS + ["fa_page_previous_solid"], width=SYM_WIDTH, 
                                        sizing_mode="fixed", button_type="light", visible=False)
        page_div = Div(text="Page:", width=30, sizing_mode="fixed", visible=False)
        layout = column([row([div, prev_page, page_div, spinner, next_page, empty], sizing_mode="stretch_width"), row([
            Div(text="", sizing_mode="stretch_width"),
            Div(text="<br>".join(checkboxes), css_classes=["vertical"], sizing_mode="fixed", 
                width=CHECK_WIDTH),
            empty
        ], sizing_mode="stretch_width"), col], sizing_mode="stretch_width", css_classes=["outlnie_border"],
        margin=DIV_MARGIN)

        self.reset_options[label] = [col, [], 1, [spinner, next_page, prev_page, page_div]]
        
        def move_element(opt, ele, up):
            idx = None
            for i, (k, v) in enumerate(opt):
                if k == ele:
                    idx = i
                    break
            if not idx is None:
                if up and idx > 0:
                    return opt[:idx-1] + [opt[idx], opt[idx-1]] + opt[idx+1:]
                elif not up and idx + 1 < len(opt):
                    return opt[:idx] + [opt[idx+1], opt[idx]] + opt[idx+2:]
            return opt

        def trigger_callback():
            cb = {}
            for n in checkboxes:
                cb[n] = []
            for n, opts in self.reset_options[label][1]:
                for opt in opts:
                    cb[checkboxes[opt]].append(n)

            callback(cb)

        def reset_event(e):
            l = []
            pos = self.reset_options[label][2] - 1
            for idx, (n, opts) in list(enumerate(self.reset_options[label][1]))[pos*ELEMENTS_PER_PAGE:(pos+1)*ELEMENTS_PER_PAGE]:
                if orderable:
                    down_button = Button(label="", css_classes=SYM_CSS + ["fa_sort_down_solid"], width=SYM_WIDTH, 
                                        height=SYM_WIDTH, sizing_mode="fixed", tags=[n], button_type="light")
                    def down_event(n):
                        self.reset_options[label][1] = move_element(self.reset_options[label][1], n, False)
                        reset_event(0)
                        trigger_callback()
                    down_button.on_click(lambda _, n=n: down_event(n))

                    up_button = Button(label="", css_classes=SYM_CSS + ["fa_sort_up_solid"], width=SYM_WIDTH, 
                                        height=SYM_WIDTH, sizing_mode="fixed", tags=[n], button_type="light")
                    def up_event(n):
                        self.reset_options[label][1] = move_element(self.reset_options[label][1], n, True)
                        reset_event(0)
                        trigger_callback()
                    up_button.on_click(lambda _, n=n: up_event(n))

                div = Div(text=n, sizing_mode="stretch_width")
                cg = CheckboxGroup(labels=[""]*len(checkboxes), active=opts, inline=True, sizing_mode="fixed",
                                   width=CHECK_WIDTH)
                def on_change(idx, cg):
                    self.reset_options[label][1][idx][1] = cg.active
                    trigger_callback()
                cg.on_change("active", lambda _1,_2,_3,idx=idx,cg=cg: on_change(idx,cg))

                if orderable:
                    l.append(row([up_button, down_button, div, cg, empty], sizing_mode="stretch_width"))
                else:
                    l.append(row([div, cg, empty], sizing_mode="stretch_width"))

            self.reset_options[label][0].children = l

        def spinner_event(x, y, z):
            if spinner.value.isdigit() and int(spinner.value) > 0 and int(spinner.value) <= len(self.reset_options[label][1]) // ELEMENTS_PER_PAGE + 1:
                self.reset_options[label][2] = int(spinner.value)
                reset_event(0)
            else:
                spinner.value = str(self.reset_options[label][2])

        spinner.on_change("value", spinner_event)

        
        def next_page_event():
            if self.reset_options[label][2] < len(self.reset_options[label][1]) // ELEMENTS_PER_PAGE + 1:
                self.reset_options[label][2] += 1
                spinner.value = str(self.reset_options[label][2])
                reset_event(0)
        next_page.on_click(lambda _, : next_page_event())
        def prev_page_event():
            if self.reset_options[label][2] > 1:
                self.reset_options[label][2] -= 1
                spinner.value = str(self.reset_options[label][2])
                reset_event(0)
        prev_page.on_click(lambda _, : prev_page_event())

        def set_options(labels, active_dict):
            self.reset_options[label][1] = []
            for x in self.reset_options[label][3]:
                x.visible = len(labels) > ELEMENTS_PER_PAGE
            for jdx, n in enumerate(labels):
                self.reset_options[label][1].append([n, []])
                for idx, cb in enumerate(checkboxes):
                    if n in active_dict[cb]:
                        self.reset_options[label][1][jdx][1].append(idx)
            reset_event(0)
            trigger_callback()

        return set_options, layout

    def config_row(self, file_nr, callback=None, lock_name=False):
        SYM_WIDTH = 10
        SYM_CSS = ["other_button"]
        with open('smoother/static/conf/' + str(file_nr) + '.json', 'r') as f:
            settings = json.load(f)

        if CONFIG_FILE_VERSION != settings["smoother_config_file_version"]:
            print("Config file version does not match: expected", CONFIG_FILE_VERSION, 
                  "but got", settings["smoother_config_file_version"])
        
        name = TextInput(value=settings["display_name"], sizing_mode="stretch_width", disabled=lock_name)
        apply_button = Button(label="", css_classes=SYM_CSS + ["fa_apply"], width=SYM_WIDTH, 
                            height=SYM_WIDTH, sizing_mode="fixed", button_type="light")
        save_button = Button(label="", css_classes=SYM_CSS + ["fa_save"], width=SYM_WIDTH, 
                            height=SYM_WIDTH, sizing_mode="fixed", button_type="light")
        def save_event():
            def dict_diff(a, b):
                r = {}
                for k in a.keys():
                    if isinstance(a[k], dict):
                        d = dict_diff(a[k], b[k])
                        if len(d) > 0:
                            r[k] = d
                    elif a[k] != b[k]:
                        r[k] = a[k]
                return r
            print("saving...")
            settings = dict_diff(self.settings, self.settings_default)
            settings["display_name"] = name.value
            settings["smoother_config_file_version"] = CONFIG_FILE_VERSION
            with open('smoother/static/conf/' + str(file_nr) + '.json', 'w') as f:
                json.dump(settings, f)
            print("saved")

        save_button.on_click(lambda _: save_event())
        return row([name, apply_button, save_button], sizing_mode="stretch_width")

    def make_slider_spinner(self, title, settings, width=200, 
                            on_change=lambda _v: None, spinner_width=80, sizing_mode="stretch_width"):
        value = settings["val"]
        start = settings["min"]
        end = settings["max"]
        step = settings["step"]
        spinner = Spinner(value=value, low=start, high=end, step=step, width=spinner_width)
        slider = Slider(title=title, value=value, start=start, end=end, step=step, show_value=False, width=width-spinner_width, sizing_mode=sizing_mode)

        spinner.js_link("value", slider, "value")
        slider.js_link("value", spinner, "value")
        slider.on_change("value_throttled", lambda _x,_y,_z: on_change(slider.value))
        spinner.on_change("value_throttled", lambda _x,_y,_z: on_change(spinner.value))

        return row([slider, spinner], width=width, margin=DIV_MARGIN)

    def make_range_slider_spinner(self, title, settings, width=200, 
                            on_change=lambda _v: None, spinner_width=80, sizing_mode="stretch_width"):
        value = [settings["val_min"], settings["val_max"]]
        start = settings["min"]
        end = settings["max"]
        step = settings["step"]
        slider = RangeSlider(title=title, value=value, start=start, end=end, step=step, show_value=False, width=width-spinner_width*2, sizing_mode=sizing_mode)
        spinner_start = Spinner(value=value[0], low=start, high=end, step=step, width=spinner_width)
        spinner_end = Spinner(value=value[1], low=start, high=end, step=step, width=spinner_width)

        spinner_start.js_on_change('value', CustomJS(args=dict(other=slider), code="other.value = [this.value, other.value[1]]" ) )
        slider.js_link("value", spinner_start, "value", attr_selector=0)

        spinner_end.js_on_change('value', CustomJS(args=dict(other=slider), code="other.value = [other.value[0], this.value]" ) )
        slider.js_link("value", spinner_end, "value", attr_selector=1)

        slider.on_change("value_throttled", lambda _x,_y,_z: on_change(slider.value))
        spinner_end.on_change("value_throttled", lambda _x,_y,_z: on_change(slider.value))
        spinner_start.on_change("value_throttled", lambda _x,_y,_z: on_change(slider.value))

        return row([slider, spinner_start, spinner_end], width=width, margin=DIV_MARGIN)

    def make_checkbox(self, title, on_change, active=True, width=200):
        div = Div(text=title, sizing_mode="stretch_width")
        cg = CheckboxGroup(labels=[""], active=[0] if active else [], sizing_mode="fixed", width=20)
        cg.on_change("active", lambda _1,_2,_3: on_change(0 in cg.active))
        return row([div, cg], width=width, margin=DIV_MARGIN)

    def __init__(self):
        self.meta = None
        self.do_render = False
        self.cancel_render = False
        self.force_render = True
        self.curdoc = curdoc()
        self.last_drawing_area = (0, 0, 0, 0)
        self.last_h_w_bin = (0, 0)
        self.curr_area_size = 1
        self.idx = None
        self.idx_norm = None
        self.render_logger = Logger()
        self.smoother_version = "?"
        self.reset_options = {}
        with open('smoother/static/conf/default.json', 'r') as f:
            self.settings_default = json.load(f)
        with open('smoother/static/conf/default.json', 'r') as f:
            self.settings = json.load(f)

        global SETTINGS_WIDTH
        tollbars = []
        self.heatmap = FigureMaker().range1d().scale().combine_tools(tollbars).get()

        d = {"b": [], "l": [], "t": [], "r": [], "c": [], "chr_x": [], "chr_y": [], "x1": [], "x2": [],
             "y1": [], "y2": [], "s": [], "d_a": [], "d_b": []}
        self.heatmap_data = ColumnDataSource(data=d)
        self.heatmap.quad(left="l", bottom="b", right="r", top="t", fill_color="c", line_color=None,
                          source=self.heatmap_data, level="underlay")
        #self.heatmap.xgrid.minor_grid_line_dash = [2, 8]
        #self.heatmap.ygrid.minor_grid_line_dash = [2, 8]
        self.heatmap.xgrid.minor_grid_line_alpha = 0.5
        self.heatmap.ygrid.minor_grid_line_alpha = 0.5

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
                ('reads by group', "A: @d_a, B: @d_b")
            ]
        ))

        self.heatmap_x_axis = FigureMaker().x_axis_of(
            self.heatmap, "DNA", True).combine_tools(tollbars).get()
        self.heatmap_y_axis = FigureMaker().y_axis_of(
            self.heatmap, "RNA", True).combine_tools(tollbars).get()

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
            self.heatmap).hidden().hide_on("ratio").combine_tools(tollbars).get()
        self.ratio_x.add_tools(ratio_hover_x)
        self.ratio_x_axis = FigureMaker().x_axis_of(
            self.ratio_x).combine_tools(tollbars).get()
        self.ratio_x_axis.xaxis.axis_label = "Ratio"
        self.ratio_x_axis.xaxis.ticker = AdaptiveTicker(desired_num_ticks=3)
        self.ratio_x.xgrid.ticker = AdaptiveTicker(desired_num_ticks=3, num_minor_ticks=1)
        self.ratio_x.xgrid.grid_line_alpha = 0
        self.ratio_x.xgrid.minor_grid_line_alpha = 0.5
        self.ratio_x.ygrid.minor_grid_line_alpha = 0.5

        self.ratio_y = FigureMaker().h(DEFAULT_SIZE).link_x(
            self.heatmap).hidden().hide_on("ratio").combine_tools(tollbars).get()
        self.ratio_y.add_tools(ratio_hover_y)
        self.ratio_y_axis = FigureMaker().y_axis_of(
            self.ratio_y).combine_tools(tollbars).get()
        self.ratio_y_axis.yaxis.axis_label = "Ratio"
        self.ratio_y_axis.yaxis.ticker = AdaptiveTicker(desired_num_ticks=3)
        self.ratio_y.ygrid.ticker = AdaptiveTicker(desired_num_ticks=3, num_minor_ticks=1)
        self.ratio_y.ygrid.grid_line_alpha = 0
        self.ratio_y.ygrid.minor_grid_line_alpha = 0.5
        self.ratio_y.xgrid.minor_grid_line_alpha = 0.5


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
        self.raw_x.xgrid.ticker = AdaptiveTicker(desired_num_ticks=3, num_minor_ticks=1)
        self.raw_x.xgrid.grid_line_alpha = 0
        self.raw_x.xgrid.minor_grid_line_alpha = 0.5
        self.raw_x.ygrid.minor_grid_line_alpha = 0.5

        self.raw_y = FigureMaker().h(DEFAULT_SIZE).link_x(
            self.heatmap).hide_on("raw").combine_tools(tollbars).get()
        self.raw_y.add_tools(raw_hover_y)
        self.raw_y_axis = FigureMaker().y_axis_of(
            self.raw_y).combine_tools(tollbars).get()
        self.raw_y_axis.yaxis.axis_label = "Cov"
        self.raw_y_axis.yaxis.ticker = AdaptiveTicker(desired_num_ticks=3)
        self.raw_y.ygrid.ticker = AdaptiveTicker(desired_num_ticks=3, num_minor_ticks=1)
        self.raw_y.ygrid.grid_line_alpha = 0
        self.raw_y.ygrid.minor_grid_line_alpha = 0.5
        self.raw_y.xgrid.minor_grid_line_alpha = 0.5

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
        self.anno_x.xgrid.minor_grid_line_alpha = 0
        self.anno_x.xgrid.grid_line_alpha = 0
        self.anno_x.ygrid.minor_grid_line_alpha = 0.5

        self.anno_y = FigureMaker().h(DEFAULT_SIZE).link_x(self.heatmap).hide_on(
            "annotation").combine_tools(tollbars).categorical_y().get()
        self.anno_y_axis = FigureMaker().y_axis_of(
            self.anno_y).combine_tools(tollbars).get()
        self.anno_y_axis.yaxis.axis_label = "Anno"
        self.anno_y.ygrid.minor_grid_line_alpha = 0
        self.anno_y.ygrid.grid_line_alpha = 0
        self.anno_y.xgrid.minor_grid_line_alpha = 0.5

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
        
        
        crosshair = CrosshairTool(dimensions="width", line_color="lightgrey")
        for fig in [self.anno_x, self.raw_x, self.ratio_x, self.heatmap]:
            fig.add_tools(crosshair)
        crosshair = CrosshairTool(dimensions="height", line_color="lightgrey")
        for fig in [self.anno_y, self.raw_y, self.ratio_y, self.heatmap]:
            fig.add_tools(crosshair)


        tool_bar = FigureMaker.get_tools(tollbars)
        #SETTINGS_WIDTH = tool_bar.width
        show_hide = FigureMaker.show_hide_dropdown(
                self.settings["interface"]["show_hide"],
                ("Axes", "axis"), (RATIO_PLOT_NAME, "ratio"), (RAW_PLOT_NAME, "raw"),
                                                   (ANNOTATION_PLOT_NAME, "annotation"), ("Tools", "tools"))

        def in_group_event(e):
            self.settings['replicates']['in_group'] = e
            self.trigger_render()
        in_group = self.dropdown_select("In Group", in_group_event, "tooltip_in_group",
                                             ("Sum [a+b+c+...]", "sum"), 
                                             ("Minimium [min(a,b,c,...)]", "min"),
                                             ("Difference [|a-b|+|a-c|+|b-c|+...]", "dif"),
                                             active_item=self.settings['replicates']['in_group'])

        def betw_group_event(e):
            self.settings['replicates']['between_group'] = e
            self.trigger_render()
        betw_group = self.dropdown_select("Between Group", betw_group_event, "tooltip_between_groups",
                                               ("Sum [(a+b)/2]", "sum"), ("Show First Group [a]", "1st"), 
                                               ("Show Second Group [b]", "2nd"), ("Substract [a-b]", "sub"),
                                               ("Difference [|a-b|]", "dif"), ("Minimum [min(a,b)]", "min"), 
                                               ("Maximum [max(a,b)]", "max"),
                                                active_item=self.settings['replicates']['between_group'])

        def symmetrie_event(e):
            self.settings['filters']['symmetry'] = e
            self.trigger_render()
        symmetrie = self.dropdown_select("Symmetry", symmetrie_event, "tooltip_symmetry",
                                              ("Show All Interactions", "all"), 
                                              ("Only Show Symmetric Interactions", "sym"),
                                              ("Only Show Asymmetric Interactions", "asym"),
                                              ("Make Interactions Symmetric (Bottom to Top)", "topToBot"), 
                                              ("Make Interactions Symmetric (Top to Bottom)", "botToTop"),
                                              active_item=self.settings['filters']['symmetry'])

        def normalization_event(e):
            self.settings['normalization']['normalize_by'] = e
            self.trigger_render()
        normalization = self.dropdown_select("Normalize by", normalization_event, "tooltip_normalize_by",
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
                                                  ("No Normalization", "dont"),
                                                  active_item=self.settings['normalization']['normalize_by']
                                                  )

        def incomp_align_event(e):
            self.settings['filters']['incomplete_alignments'] = e
            self.trigger_render()
        incomp_align_layout = self.make_checkbox("Show reads with incomplete alignments", 
                                                    incomp_align_event, 
                                                    self.settings['filters']['incomplete_alignments'])

        def ddd_event(e):
            self.settings['normalization']['ddd'] = e
            self.trigger_render()
        ddd = self.dropdown_select("Distance Dependent Decay", ddd_event, "tooltip_ddd",
                                        ("Keep decay", "no"), ("Normalize decay away", "yes"),
                                        active_item=self.settings['normalization']['ddd'])

        def square_bin_event(val):
            self.settings["interface"]["bin_aspect_ratio"] = val
            self.trigger_render()
        square_bins = self.dropdown_select("Bin Aspect Ratio", square_bin_event, "tooltip_bin_aspect_ratio",
                                                  ("Squared relative to view",
                                                   "view"),
                                                  ("Squared relative to coordinates",
                                                   "coord"),
                                                   active_item=self.settings["interface"]["bin_aspect_ratio"]
                                                   )
        def power_ten_bin_event(val):
            self.settings["interface"]["snap_bin_size"] = val
            self.trigger_render()
        power_ten_bin = self.dropdown_select("Snap Bin Size", power_ten_bin_event, "tooltip_snap_bin_size",
                                                ("Do not snap", "no"),
                                                ("To Even Power of Ten", "p10"),
                                                active_item=self.settings["interface"]["snap_bin_size"]
                                            )

        def color_event(val):
            self.settings["interface"]["color_palette"] = val
            self.trigger_render()
        color_picker = self.dropdown_select("Color Palette", color_event, "tooltip_color",
                                                ("Viridis", "Viridis256"),
                                                ("Plasma", "Plasma256"),
                                                ("Turbo", "Turbo256"),
                                                ("Low to High", "LowToHigh"),
                                                active_item=self.settings["interface"]["color_palette"]
                                                  )

        def multi_mapping_event(e):
            self.settings["filters"]["ambiguous_mapping"] = e
            self.trigger_render()
        multi_mapping = self.dropdown_select("Ambiguous Mapping", multi_mapping_event, "tooltip_multi_mapping",
                                                ("Count read if all mapping loci are within a bin", "enclosed"),
                                                ("Count read if mapping loci bounding-box overlaps bin", "overlaps"),
                                                ("Count read if first mapping loci is within a bin", "first"),
                                                ("Count read if last mapping loci is within a bin", "last"),
                                                ("Count read if there is only one mapping loci", "points_only"),
                                                active_item=self.settings["filters"]["ambiguous_mapping"]
                                                  )

        def axis_labels_event(e):
            self.settings["interface"]["axis_lables"] = e
            self.heatmap_y_axis.yaxis.axis_label = e.split("_")[0]
            self.heatmap_x_axis.xaxis.axis_label = e.split("_")[1]
        axis_lables = self.dropdown_select("Axis Labels", axis_labels_event, "tooltip_y_axis_label",
                                                  ("RNA / DNA", "RNA_DNA"),
                                                  ("DNA / RNA", "DNA_RNA"),
                                                  ("DNA / DNA", "DNA_DNA"), 
                                                  active_item=self.settings["interface"]["axis_lables"]
                                                  )

        def stretch_event(val):
            self.settings["interface"]["stretch_or_scale"] = val
            self.heatmap.sizing_mode = val
        stretch_event(self.settings["interface"]["stretch_or_scale"])
        self.stretch = self.dropdown_select("Stretch/Scale", stretch_event, "tooltip_stretch_scale",
                                                  ("Scale", "scale_height"),
                                                  ("Stretch", "stretch_both"),
                                            active_item=self.settings["interface"]["stretch_or_scale"])

        def maping_quality_event(val):
            self.settings["filters"]["mapping_q"]["val_min"] = val[0]
            self.settings["filters"]["mapping_q"]["val_max"] = val[1]
            self.trigger_render()
        ms_l = self.make_range_slider_spinner(width=SETTINGS_WIDTH, 
                                                settings=self.settings["filters"]["mapping_q"], 
                                                title="Mapping Quality Bounds", sizing_mode="stretch_width",
                                       on_change=maping_quality_event)

        def interactions_event(val):
            self.settings["normalization"]["min_interactions"]["val"] = val
            self.trigger_render()
        ibs_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                                                title="Minimum Interactions", 
                                                settings=self.settings["normalization"]["min_interactions"], 
                                                on_change=interactions_event, 
                                                sizing_mode="stretch_width")
        

        def color_range_slider_event(val):
            self.settings["normalization"]["color_range"]["val_start"] = val[0]
            self.settings["normalization"]["color_range"]["val_end"] = val[1]
            self.trigger_render()
        crs_l = self.make_range_slider_spinner(width=SETTINGS_WIDTH, 
                                                title="Color Scale Range", 
                                                settings=self.settings["normalization"]["color_range"],
                                                sizing_mode="stretch_width",
                                                on_change=color_range_slider_event)

        def log_base_event(val):
            self.settings["normalization"]["log_base"]["val"] = val
            self.trigger_render()
        is_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                                          title="Color Scale Log Base", 
                                          settings=self.settings["normalization"]["log_base"],
                                          on_change=log_base_event,
                                          sizing_mode="stretch_width")

        def update_freq_event(val):
            self.settings["interface"]["update_freq"]["val"] = val
        ufs_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                                            settings=self.settings["interface"]["update_freq"],
                                              title="Update Frequency [seconds]" #, format="0[.]000"
                                              , on_change=update_freq_event, sizing_mode="stretch_width")


        def redraw_slider_event(val):
            self.settings["interface"]["zoom_redraw"]["val"] = val
            self.trigger_render()
        rs_l = self.make_slider_spinner(width=SETTINGS_WIDTH,
                                    settings=self.settings["interface"]["zoom_redraw"],
                                    on_change=redraw_slider_event,
                                    title="Redraw if zoomed in by [%]", sizing_mode="stretch_width")

        def add_area_event(val):
            self.settings["interface"]["add_draw_area"]["val"] = val
            self.trigger_render()
        aas_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                                        settings=self.settings["interface"]["add_draw_area"],
                                      on_change=add_area_event,
                                      title="Additional Draw Area [%]", sizing_mode="stretch_width")

        def diag_dist_event(val):
            self.settings["filters"]["min_diag_dist"]["val"] = val
            self.trigger_render()
        dds_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                                    settings=self.settings["filters"]["min_diag_dist"],
                                       on_change=diag_dist_event,
                                       title="Minimum Distance from Diagonal (kbp)", sizing_mode="stretch_width")

        def anno_size_slider_event(val):
            self.settings["interface"]["anno_size"]["val"] = val
            self.anno_x.width = val
            self.anno_x_axis.width = val
            self.anno_y.height = val
            self.anno_y_axis.height = val
        anno_size_slider_event(self.settings["interface"]["anno_size"]["val"])
        ass_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                                      settings=self.settings["interface"]["anno_size"],
                                       title=ANNOTATION_PLOT_NAME + " Plot Size", sizing_mode="stretch_width",
                                       on_change=anno_size_slider_event)

        def ratio_size_slider_event(val):
            self.settings["interface"]["ratio_size"]["val"] = val
            self.ratio_x.width = val
            self.ratio_x_axis.width = val
            self.ratio_y.height = val
            self.ratio_y_axis.height = val
        ratio_size_slider_event(self.settings["interface"]["ratio_size"]["val"])
        rss1_l = self.make_slider_spinner(width=SETTINGS_WIDTH,
                                      settings=self.settings["interface"]["ratio_size"],
                                        title=RATIO_PLOT_NAME + " Plot Size", sizing_mode="stretch_width",
                                        on_change=ratio_size_slider_event)

        def raw_size_slider_event(val):
            self.settings["interface"]["raw_size"]["val"] = val
            self.raw_x.width = val
            self.raw_x_axis.width = val
            self.raw_y.height = val
            self.raw_y_axis.height = val
        raw_size_slider_event(self.settings["interface"]["raw_size"]["val"])
        rss2_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                                      settings=self.settings["interface"]["raw_size"],
                                      title=RAW_PLOT_NAME + " Plot Size", sizing_mode="stretch_width",
                                      on_change=raw_size_slider_event)

        def num_bins_event(val):
            self.settings["interface"]["max_num_bins"]["val"] = val
            self.trigger_render()
        nb_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                               settings=self.settings["interface"]["max_num_bins"],
                               on_change=num_bins_event,
                               title="Max number of Bins (in thousands)", sizing_mode="stretch_width")

        def radicl_seq_accept_event(val):
            self.settings["normalization"]["p_accept"]["val"] = val
            self.trigger_render()
        rsa_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                               settings=self.settings["normalization"]["p_accept"],
                               title="pAccept for binominal test", sizing_mode="stretch_width",
                               on_change=radicl_seq_accept_event)
            
        meta_file_label = Div(text="Data path:")
        meta_file_label.margin = DIV_MARGIN
        self.meta_file = TextInput(value="smoother_out/")
        self.meta_file.on_change("value", lambda x, y, z: self.setup())

        self.group_a = set()
        self.group_b = set()
        def group_event(sele):
            self.group_a = set(sele["A"])
            self.group_b = set(sele["B"])
            self.trigger_render()
        self.set_group, group_layout = self.multi_choice("Group", ["A", "B"], group_event, True)

        self.displayed_annos = []
        self.filtered_annos_x = []
        self.filtered_annos_y = []
        def anno_event(sele):
            self.displayed_annos = sele["Displayed"][::-1]
            self.filtered_annos_x = sele["Row filter"]
            self.filtered_annos_y = sele["Column filter"]
            self.trigger_render()
        self.set_annos, annos_layout = self.multi_choice("Annotations", 
                                                         ["Displayed", "Row filter", "Column filter"],
                                                         anno_event)

        power_tick = FuncTickFormatter(
            code="""
            if (tick / 9 >= 7)
                return Math.ceil((1 + tick % 9)) + "*10^" + Math.floor(tick / 9) + "bp";
            else if (tick / 9 >= 3)
                return Math.ceil((1 + tick % 9) * Math.pow(10, Math.floor(tick / 9)-3)) + "kbp";
            else
                return Math.ceil((1 + tick % 9) * Math.pow(10, Math.floor(tick / 9))) + "bp"; """)
        self.min_max_bin_size = Slider(
                start=self.settings["interface"]["min_bin_size"]["min"], 
                end=self.settings["interface"]["min_bin_size"]["max"], 
                value=self.settings["interface"]["min_bin_size"]["val"], 
                step=self.settings["interface"]["min_bin_size"]["step"], 
                title="Minimum Bin Size",
                format=power_tick, 
                sizing_mode="stretch_width")
        def min_bin_size_event():
            self.settings["interface"]["min_bin_size"]["val"] = self.min_max_bin_size.value
            self.trigger_render()
        self.min_max_bin_size.on_change("value_throttled", lambda x, y, z: min_bin_size_event())

        def callback(a):
            self.min_max_bin_size.value = \
                min(max(self.min_max_bin_size.value + a, self.min_max_bin_size.start), self.min_max_bin_size.end)
            min_bin_size_event()
        button_s_up = Button(label="", css_classes=["other_button", "fa_sort_up_solid"], 
                                button_type="light", width=10, height=10)
        button_s_up.on_click(lambda _: callback(1))
        button_s_down = Button(label="", css_classes=["other_button", "fa_sort_down_solid"],
                                button_type="light", width=10, height=10)
        button_s_down.on_click(lambda _: callback(-1))

        mmbs_l = row([self.min_max_bin_size, column([button_s_up, button_s_down])], margin=DIV_MARGIN)

        self.curr_bin_size = Div(text="Waiting for Fileinput.", sizing_mode="stretch_width")
        
        self.spinner = Div(text="<div class=\"lds-spinner\"><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div></div>")
        #self.spinner = Div(text="<div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div>", css_classes=["lds-spinner"])
        self.spinner.css_classes = ["fade-out"]

        self.info_field = row([self.spinner, self.curr_bin_size], css_classes=["twenty_percent"])
        self.info_field.height = 100
        self.info_field.min_height = 100
        self.info_field.height_policy = "fixed"

        self.norm_x = []
        self.norm_y = []
        def norm_event(sele):
            self.norm_x = sele["Rows"]
            self.norm_y = sele["Columns"]
            self.trigger_render()
        self.set_norm, norm_layout = self.multi_choice("Normalization", ["Rows", "Columns"], norm_event)

        def x_coords_event(e):
            FigureMaker.x_coords_d = e
            self.setup_coordinates()
            self.trigger_render()
        x_coords, self.x_coords_update = self.dropdown_select_h("Column Coordinates", x_coords_event,
                                                                 "tooltip_row_coordinates")

        def y_coords_event(e):
            FigureMaker.y_coords_d = e
            self.setup_coordinates()
            self.trigger_render()
        y_coords, self.y_coords_update = self.dropdown_select_h("Row Coordinates", y_coords_event,
                                                                 "tooltip_column_coordinates")

        self.chrom_x = []
        self.chrom_y = []
        def chrom_event(sele):
            self.chrom_x = sele["Rows"][::-1]
            self.chrom_y = sele["Columns"][::-1]
            self.setup_coordinates()
            self.trigger_render()
        self.set_chrom, chrom_layout = self.multi_choice("Chromosomes", ["Rows", "Columns"], chrom_event)

        def multiple_anno_per_bin_event(e):
            self.settings["filters"]["multiple_annos_in_bin"] = e
            self.trigger_render()
        multiple_anno_per_bin = self.dropdown_select("Multiple Annotations in Bin", multiple_anno_per_bin_event, 
                "tooltip_multiple_annotations_in_bin", 
                ("Combine region from first to last annotation", "combine"), 
                ("Use first annotation", "first"), 
                ("Use Random annotation", "random"), 
                ("Increase number of bins to match number of annotations (might be slow)", "force_separate"),
                active_item=self.settings["filters"]["multiple_annos_in_bin"])

        self.do_export = None
        def export_event(e):
            self.do_export = e
            self.trigger_render()
        self.export_button = self.dropdown_select("Export", export_event, "tooltip_export",
                                                  ("Current View", "current"),
                                                  ("Full Matrix", "full"))

        export_label = Div(text="Output Prefix:")
        export_label.margin = DIV_MARGIN
        export_file = TextInput(value=self.settings["export"]["prefix"])
        def export_file_event(_1, _2, _3):
            self.settings["export"]["prefix"] = export_file.value
            self.trigger_render()
        export_file.on_change("value", export_file_event)
        
        def export_sele_event(sele):
            self.settings["export"]["selection"] = sele[""]
            self.trigger_render()
        set_export_sele, export_sele_layout = self.multi_choice("Export Selection", [""], export_sele_event, False)
        set_export_sele(
            ["Heatmap", "Column Sum", "Row Sum", "Include Annotation"],
            {"": self.settings["export"]["selection"]}
        )
    
        self.export_type = []
        def export_type_event(sele):
            self.export_type = sele[""]
            self.trigger_render()
        set_export_type, export_type_layout = self.multi_choice("Export Type", [""], export_type_event)
        set_export_type(["Data"], {"":[]})
        
        grid_seq_config = Button(label="Grid Seq-like @todo", sizing_mode="stretch_width", 
                                 css_classes=["other_button", "tooltip", "tooltip_grid_seq"],
                                 height=DROPDOWN_HEIGHT)
        def grid_seq_event(e):
            # @todo 
            self.trigger_render()
        grid_seq_config.on_click(grid_seq_event)
        radicl_seq_config = Button(label="Radicl Seq-like", sizing_mode="stretch_width", 
                                   css_classes=["other_button", "tooltip", "tooltip_radicl_seq"],
                                   height=DROPDOWN_HEIGHT)
        def radicl_seq_event(e):
            # @todo 
            self.trigger_render()
        radicl_seq_config.on_click(radicl_seq_event)

        low_color = ColorPicker(title="Color Low", color=self.settings["interface"]["color_low"])
        high_color = ColorPicker(title="Color High", color=self.settings["interface"]["color_high"])
        def color_event(_1, _2, _3):
            self.settings["interface"]["color_low"] = self.low_color.color
            self.settings["interface"]["color_high"] = self.high_color.color
            self.trigger_render()
        low_color.on_change("color", color_event)
        high_color.on_change("color", color_event)

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
                # remove and read children to force re-layout
                tmp = cx.children
                cx.children = []
                cx.visible = t.active
                cx.children = tmp
            t.on_click(callback)
            callback(None)
            return r

        with open("smoother/VERSION", "r") as in_file:
            self.smoother_version = in_file.readlines()[0][:-1]

        version_info = Div(text="Smoother "+ self.smoother_version +"<br>LibSps Version: " + bin.libSps.VERSION)

        self.color_mapper = LinearColorMapper(palette=["black"], low=0, high=1)
        color_figure = figure(tools='', height=0)
        color_figure.x(0,0)
        self.color_info = ColorBar(color_mapper=self.color_mapper, orientation="horizontal", 
                                   ticker=FixedTicker(ticks=[]))
        self.color_info.formatter = FuncTickFormatter(
                        args={"ticksx": [], "labelsx": []},
                        code="""
                            for (let i = 0; i < ticksx.length; i++)
                                if(tick == ticksx[i])
                                    return labelsx[i];
                            return "n/a";
                        """)
        color_figure.add_layout(self.color_info, "below")

        # make plot invisible
        color_figure.axis.visible = False
        color_figure.toolbar_location = None
        color_figure.border_fill_alpha = 0
        color_figure.outline_line_alpha = 0

        quick_configs = [self.config_row("default", lock_name=True)]
        for idx in range(1,6):
            quick_configs.append(self.config_row(idx))

        _settings = column([
                make_panel("General", "tooltip_general", [tool_bar, meta_file_label, self.meta_file]),
                make_panel("Normalization", "tooltip_normalization", [normalization, color_figure,
                                    ibs_l, crs_l, is_l, norm_layout, rsa_l, ddd]),
                make_panel("Replicates", "tooltip_replicates", [in_group, betw_group, group_layout]),
                make_panel("Interface", "tooltip_interface", [nb_l,
                                    show_hide, mmbs_l,
                                    ufs_l, rs_l, aas_l, ass_l, rss1_l, rss2_l,
                                    self.stretch, square_bins, power_ten_bin, color_picker, 
                                    low_color, high_color, axis_lables, self.overlay_dataset_id]),
                make_panel("Filters", "tooltip_filters", [ms_l, incomp_align_layout, 
                                          symmetrie, dds_l, annos_layout, 
                                          x_coords, y_coords, multiple_anno_per_bin, chrom_layout, multi_mapping]),
                make_panel("Export", "tooltip_export", [export_label, export_file, export_sele_layout,
                                        #export_type_layout, 
                                      self.export_button]),
                make_panel("Quick Config", "tooltip_quick_config", [grid_seq_config, radicl_seq_config, 
                                                                    *quick_configs]),
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
        self.settings_row = row([Spacer(sizing_mode="stretch_both"), _settings_n_info, FigureMaker.reshow_settings()], css_classes=["full_height"])
        self.settings_row.height = 100
        self.settings_row.min_height = 100
        self.settings_row.height_policy = "fixed"
        self.settings_row.width = SETTINGS_WIDTH
        self.settings_row.width_policy = "fixed"

        quit_ti = TextInput(value="keepalive", name="quit_ti", visible=False)
        quit_ti.on_change("value", lambda x, y, z: sys.exit())


        grid_layout = [
            [self.heatmap_y_axis, self.anno_x,   self.raw_x,
                self.ratio_x,      None,              self.heatmap,   self.settings_row],
            [None,              self.anno_x_axis, self.raw_x_axis,
                self.ratio_x_axis, None,              None,               None],
            [None,              None,             None,            None,
                self.ratio_y_axis, self.ratio_y,       None],
            [None,              None,             None,            None,
                self.raw_y_axis,   self.raw_y,         None],
            [None,              None,             None,            None,
                self.anno_y_axis,  self.anno_y,        None],
            [quit_ti,       None,             None,            None,
                None,            self.heatmap_x_axis, None],
        ]


        self.root = grid(grid_layout) # , sizing_mode="stretch_both"
        FigureMaker().update_visibility()

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
            if self.cancel_render:
                return
            if self.settings['normalization']['normalize_by'] == "hi-c":
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
                                                                self.settings["filters"]["multiple_annos_in_bin"], 
                                                                is_canceld=lambda: self.cancel_render)
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
            filter_l = self.filtered_annos_y
        anno_coords = None
        if FigureMaker.x_coords_d != "full_genome":
            anno_coords = FigureMaker.x_coords_d
        return self.bin_cols_or_rows(area, h_bin, 0, none_for_chr_border, filter_l, self.chrom_x, anno_coords)

    def bin_rows(self, area, h_bin, none_for_chr_border=False, filter_l=None):
        if filter_l is None:
            filter_l = self.filtered_annos_x
        anno_coords = None
        if FigureMaker.y_coords_d != "full_genome":
            anno_coords = FigureMaker.y_coords_d
        return self.bin_cols_or_rows(area, h_bin, 1, none_for_chr_border, filter_l, self.chrom_y, anno_coords)

    def bin_coords(self, area, h_bin, w_bin):
        self.render_step_log("bin_coords")
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
        if self.settings['filters']['symmetry'] == "botToTop":
            if x >= y:
                return y, x, h, w
        if self.settings['filters']['symmetry'] == "topToBot":
            if y >= x:
                return y, x, h, w
        return x, y, w, h

    def make_bins(self, bin_coords, name="make_bins"):
        #self.render_step_log(name)
        self.render_step_log(name + "_ini")
        min_ = self.settings["normalization"]["min_interactions"]["val"]
        map_q_min = self.settings["filters"]["mapping_q"]["val_min"]
        map_q_max = self.settings["filters"]["mapping_q"]["val_max"]
        if not (map_q_min == 0 and self.settings['filters']['incomplete_alignments']):
            map_q_min += 1
        manhatten_dist = 1000 * self.settings["filters"]["min_diag_dist"]["val"] / self.meta.dividend
        bins_to_search_map_q = []
        bins_to_search_no_map_q = []
        self.render_step_log(name + "_pre")
        for x, y, w, h in bin_coords:
            if abs(x - y) >= manhatten_dist:
                x, y, w, h = self.adjust_bin_pos_for_symmetrie(x, y, w, h)
                bins_to_search_map_q.append(self.idx.to_query(y, y+h, x, x+w, map_q_min, map_q_max, True, True))
                bins_to_search_no_map_q.append(self.idx.to_query(y, y+h, x, x+w, map_q_min, map_q_max, False, True))
            else:
                bins_to_search_map_q.append(self.idx.to_query(0, 0, 0, 0, 0, 0, True, True))
                bins_to_search_no_map_q.append(self.idx.to_query(0, 0, 0, 0, 0, 0, False, True))
            if self.cancel_render:
                return
        self.render_step_log(name + "_main")
        ns = []
        for name in list(self.group_a) + list(self.group_b):
            idx, _1, _2, map_q, multi_map = self.meta.datasets[name]
            ns.append(self.idx.count_multiple(idx, bins_to_search_map_q if map_q else bins_to_search_no_map_q, 
                                              self.settings["filters"]["ambiguous_mapping"], map_q, multi_map))
            if self.cancel_render:
                return

        self.render_step_log(name + "_post")

        for idx in range(len(ns)):
            for jdx in range(len(ns[idx])):
                ns[idx][jdx] = max(ns[idx][jdx] - min_, 0)
            if self.cancel_render:
                return

        return ns

    def col_norm(self, cols):
        x = self.make_bins([(c[0], 0, c[1], self.meta.chr_sizes.chr_start_pos["end"])
                                        if not c is None else (-2, -2, 1, 1) for c in cols], name="make_col_norm_bins")
        if self.cancel_render:
            return
        return self.flatten_bins(x)

    def row_norm(self, rows):
        x = self.make_bins([(0, c[0], self.meta.chr_sizes.chr_start_pos["end"], c[1])
                                        if not c is None else (-2, -2, 1, 1) for c in rows], name="make_row_norm_bins")
        if self.cancel_render:
            return
        return self.flatten_bins(x)

    def read_norm(self, in_group_a):
        n = []
        map_q_min = self.settings["filters"]["mapping_q"]["val_min"]
        map_q_max = self.settings["filters"]["mapping_q"]["val_max"]
        if not (map_q_min == 0 and self.settings['filters']['incomplete_alignments']):
            map_q_min += 1
        for name in self.group_a if in_group_a else self.group_b:
            idx, _1, _2, map_q, multi_map = self.meta.datasets[name]
            val = self.idx.count(idx, 0, self.meta.chr_sizes.chr_start_pos["end"], 0, 
                                    self.meta.chr_sizes.chr_start_pos["end"], map_q_min, map_q_max, 
                                    self.settings["filters"]["ambiguous_mapping"], map_q, multi_map)
            n.append(val)
        if self.settings['replicates']['in_group'] == "min":
            n = min(n)
        elif self.settings['replicates']['in_group'] == "sum":
            n = sum(n)
        elif self.settings['replicates']['in_group'] == "dif":
            n = sum(abs(x-y) for x in n for y in n)
        else:
            raise RuntimeError("Unknown in group value")
        return n

    def norm_num_reads(self, rows):
        if len((self.norm_x if rows else self.norm_y)) == 0:
            return 1
        map_q_min = self.settings["filters"]["mapping_q"]["val_min"]
        map_q_max = self.settings["filters"]["mapping_q"]["val_max"]
        if not (map_q_min == 0 and self.settings['filters']['incomplete_alignments']):
            map_q_min += 1
        return self.flatten_norm([
            [self.idx_norm.count(int(idx), 0, self.meta.chr_sizes.chr_start_pos["end"], map_q_min, map_q_max) \
                if self.meta.norm_via_tree(int(idx)) \
                else self.meta.norm[int(idx)].count(0, self.meta.chr_sizes.chr_start_pos["end"]) \
                for idx in (self.norm_x if rows else self.norm_y)]])[0]

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


    def norm_ddd(self, bins_l, bin_coords):
        if self.settings['normalization']['ddd'] == "no":
            return bins_l
        ret = []
        for bins in bins_l:
            ret.append([x/self.meta.get_dist_dep_decay(
                x_chr, x_2 * self.meta.dividend, y_chr, y_2 * self.meta.dividend) \
                        for x, (x_chr, x_2, y_chr, y_2) in zip(bins, bin_coords)])
        return ret

    def norm_bins(self, w_bin, bins_l, cols, rows):
        if self.settings['normalization']['normalize_by'] == "dont":
            return bins_l
        ret = []
        if self.settings['normalization']['normalize_by'] in ["tracks_abs", "tracks_rel"]:
            raw_x_norm = self.linear_bins_norm(rows, True)
            if self.cancel_render:
                return
            raw_x_norm = raw_x_norm[0]
            raw_y_norm = self.linear_bins_norm(cols, False)
            if self.cancel_render:
                return
            raw_y_norm = raw_y_norm[0]
        if self.settings['normalization']['normalize_by'] in ["column"]:
            ns = self.col_norm(cols)
        if self.settings['normalization']['normalize_by'] in ["row", "radicl-seq"]:
            ns = self.row_norm(rows)
        if self.cancel_render:
            return
        for idx, bins in enumerate(bins_l):
            if self.settings['normalization']['normalize_by'] == "max_bin_visible":
                n = max(max(bins), 1) if len(bins) > 0 else 1
                ret.append([x/n for x in bins])
            elif self.settings['normalization']['normalize_by'] == "rpm":
                n = max(self.read_norm(idx == 0), 1)
                ret.append([1000000 * x/n for x in bins])
            elif self.settings['normalization']['normalize_by'] == "rpk":
                n = max(self.read_norm(idx == 0), 1)
                ret.append([1000 * x/n for x in bins])
            elif self.settings['normalization']['normalize_by'] == "column":
                ret.append([x / max(ns[idx][idx_2 // len(rows)], 1) for idx_2, x in enumerate(bins)])
            elif self.settings['normalization']['normalize_by'] == "row":
                ret.append([x / max(ns[idx][idx_2 % len(rows)], 1) for idx_2, x in enumerate(bins)])
            elif self.settings['normalization']['normalize_by'] == "radicl-seq":
                ret.append([0]*(len(rows)*len(cols)))
                for idx_2 in range(len(rows)):
                    row = bins[idx_2::len(rows)]
                    for idx_3, v in enumerate(radicl_seq_norm(row, ns[idx][idx_2], w_bin, 
                                                   self.meta.chr_sizes.chr_start_pos["end"],
                                                   self.settings["normalization"]["min_interactions"]["val"])):
                        ret[-1][idx_2 + idx_3 * len(rows)] = v
            elif self.settings['normalization']['normalize_by'] in ["tracks_abs", "tracks_rel"]:
                n = self.read_norm(idx)

                def get_norm(i):
                    d = (raw_y_norm[i // len(rows)] * raw_x_norm[i % len(rows)] * n)
                    if d == 0:
                        return 0
                    return (self.norm_num_reads(True) * self.norm_num_reads(False)) / d
                ret.append([x*get_norm(idx_2) for idx_2, x in enumerate(bins)])
                if self.settings['normalization']['normalize_by'] == "tracks_rel":
                    _max = max(*ret[-1], 0)
                    if _max > 0:
                        for i in range(len(ret[-1])):
                            ret[-1][i] = ret[-1][i] / _max
                else:
                    for i in range(len(ret[-1])):
                        ret[-1][i] = min(ret[-1][i], 1)
            elif self.settings['normalization']['normalize_by'] == "hi-c":
                ret.append(self.hi_c_normalization(bins, rows, cols))
            else:
                raise RuntimeError("Unknown normalization value")
        return ret

    def flatten_bins(self, bins):
        if len(bins) > 0:
            self.render_step_log("flatten_bins", 0, len(bins[0]))
            group_a = range(len(self.group_a))
            group_b = range(len(self.group_a), len(self.group_a) + len(self.group_b))
            ret = [[], []]
            for idx, _ in enumerate(bins[0]):
                self.render_step_log("flatten_bins", idx, len(bins[0]))
                a = []
                b = []
                for idx_2 in group_a:
                    a.append(bins[idx_2][idx])
                for idx_2 in group_b:
                    b.append(bins[idx_2][idx])
                if self.settings['replicates']['in_group'] == "min":
                    aa = min(a) if len(a) > 0 else 0
                    bb = min(b) if len(b) > 0 else 0
                elif self.settings['replicates']['in_group'] == "sum":
                    aa = sum(a)
                    bb = sum(b)
                elif self.settings['replicates']['in_group'] == "dif":
                    aa = sum(abs(x-y) for x in a for y in a)
                    bb = sum(abs(x-y) for x in b for y in b)
                else:
                    raise RuntimeError("Unknown in group value")
                ret[0].append(aa)
                ret[1].append(bb)
            return ret
        return [[], []]

    def flatten_norm(self, bins):
        ret = []
        for x in bins:
            if x is None:
                ret.append(x)
            elif self.settings['replicates']['in_group'] == "min":
                ret.append(min(x))
            elif self.settings['replicates']['in_group'] == "sum":
                ret.append(sum(x))
            elif self.settings['replicates']['in_group'] == "dif":
                ret.append(sum(abs(a-b) for a in x for b in x))
        return ret

    # used function:
    # copy paste into https://www.desmos.com/calculator/auubsajefh
    # y=\frac{\log\left(2^{a}\cdot\left(x\cdot\left(1-\frac{1}{2^{a}}\right)+\frac{1}{2^{a}}\right)\right)}{\log\left(2^{a}\right)}
    def log_scale(self, c):
        if self.settings["normalization"]["log_base"]["val"] == 0:
            return c
        a = 2**self.settings["normalization"]["log_base"]["val"]
        c = math.log(  a*( min(1,c)*( 1 - (1/a) ) + (1/a) )  ) / math.log(a)
        return c

    def color_bins_a(self, bins):
        ret = []
        for x, y in zip(*bins):
            c = 0
            if self.settings['replicates']['between_group'] == "1st":
                c = x
            elif self.settings['replicates']['between_group'] == "2nd":
                c = y
            elif self.settings['replicates']['between_group'] == "sub":
                c = (x - y)
            elif self.settings['replicates']['between_group'] == "min":
                c = min(x, y)
            elif self.settings['replicates']['between_group'] == "max":
                c = max(x, y)
            elif self.settings['replicates']['between_group'] == "dif":
                c = abs(x - y)
            elif self.settings['replicates']['between_group'] == "sum":
                c = (x + y) / 2
            else:
                raise RuntimeError("Unknown between group value")
            ret.append(c)
        return ret

    def combine_hex_values(self, d):
        ## taken from: https://stackoverflow.com/questions/61488790/how-can-i-proportionally-mix-colors-in-python
        d_items = sorted(d.items())
        tot_weight = sum(d.values())
        red = int(sum([int(k[:2], 16)*v for k, v in d_items])/tot_weight)
        green = int(sum([int(k[2:4], 16)*v for k, v in d_items])/tot_weight)
        blue = int(sum([int(k[4:6], 16)*v for k, v in d_items])/tot_weight)
        zpad = lambda x: x if len(x)==2 else '0' + x
        return zpad(hex(red)[2:]) + zpad(hex(green)[2:]) + zpad(hex(blue)[2:])

    def color(self, x):
        if self.settings["interface"]["color_palette"] == "Viridis256":
            return Viridis256[x]
        if self.settings["interface"]["color_palette"] == "Plasma256":
            return Plasma256[x]
        if self.settings["interface"]["color_palette"] == "Turbo256":
            return Turbo256[x]
        if self.settings["interface"]["color_palette"] == "LowToHigh":
            return "#" + self.combine_hex_values({self.settings["interface"]["color_low"][1:]: 1-x/255, 
                                                  self.settings["interface"]["color_high"][1:]: x/255})
        return Viridis256[x]

    def color_range(self, c):
        if self.settings["normalization"]["color_range"]["val_max"] == \
                self.settings["normalization"]["color_range"]["val_min"]:
            return 0
        c = (c - self.settings["normalization"]["color_range"]["val_min"]) / (
                self.settings["normalization"]["color_range"]["val_max"] - self.settings["normalization"]["color_range"]["val_min"])
        return max(0, min(MAP_Q_MAX-1, int((MAP_Q_MAX-1)*c)))

    def color_bins_c(self, c):
        if self.settings['replicates']['between_group'] == "sub":
            c = self.log_scale(abs(c)) * (1 if c >= 0 else -1) / 2 + 0.5
            c = self.color_range(c) 
        else:
            if math.isnan(self.log_scale(c)):
                return 0
            else:
                c = self.color_range(self.log_scale(c))
        return c

    
    def color_bins_b(self, bins):
        ret = []
        for c in bins:
            ret.append(self.color(self.color_bins_c(c)))
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
        if self.settings['filters']['symmetry'] == "all":
            return bins
        elif self.settings['filters']['symmetry'] == "sym" or self.settings['filters']['symmetry'] == "asym":
            bins_2 = self.make_bins([(y, x, h, w) for x, y, w, h in bin_coords], name="make_bins_symmetrie")
            if self.cancel_render:
                return
            norms = self.norm_bins(h_bin, bins_2, bin_rows, bin_cols)
            if self.cancel_render:
                return
            if self.settings['filters']['symmetry'] == "sym":
                return [[min(a, b) for a, b in zip(bin, norm)] for bin, norm in zip(bins, norms)]
            else:
                return [[max(a-b, 0) for a, b in zip(bin, norm)] for bin, norm in zip(bins, norms)]
        else:
            return bins

    def annotation_bins(self, bins, coverage_obj):
        return [coverage_obj.count(x[0], x[0] + x[1]) if not x is None else float('NaN') for x in bins]

    def linear_bins_norm(self, bins, rows):
        vals = []
        idxs = [idx for idx, name in self.meta.normalizations.items() if name[0] in (self.norm_x if rows else self.norm_y)]
        map_q_min = self.settings["filters"]["mapping_q"]["val_min"]
        map_q_max = self.settings["filters"]["mapping_q"]["val_max"]
        if not (map_q_min == 0 and self.settings['filters']['incomplete_alignments']):
            map_q_min += 1
        for x in bins:
            vals.append([])
            if len(idxs) == 0:
                pass
                #vals[-1].append(1)
            else:
                for idx in idxs:
                    if x is None:
                        vals[-1].append(float('NaN'))
                    else:
                        if self.meta.norm_via_tree(int(idx)):
                            vals[-1].append(self.idx_norm.count(int(idx), x[0], x[0] + x[1], map_q_min, map_q_max))
                        else:
                            vals[-1].append(self.meta.norm[int(idx)].count(x[0], x[0] + x[1]))
                    if self.cancel_render:
                        return
        return self.flatten_norm(vals), vals

    def render_log_callback(self, s):
        print(s, end="\033[K\r")

        def callback():
            self.curr_bin_size.text = s.replace(". ", "<br>")
        self.curdoc.add_next_tick_callback(callback)

    def new_render(self, reason):
        self.render_logger.new_render(reason, callback=lambda s: self.render_log_callback(s))

    def render_step_log(self, step_name="", sub_step=0, sub_step_total=None):
        self.render_logger.render_step_log(step_name, sub_step, sub_step_total, callback=lambda s: self.render_log_callback(s))

    def render_done(self, bin_amount):
        return self.render_logger.render_done(bin_amount)


    def make_anno_str(self, s, e):
        anno_str = ""
        if "Include Annotation" in self.settings["export"]["selection"]:
            for anno in self.displayed_annos:
                c = self.meta.annotations[anno].count(s, e)
                if c > 0 and c <= 10:
                    if len(anno_str) > 0:
                        anno_str += "; "
                    anno_str += anno + ": {" + self.meta.annotations[anno].info(s, e).replace("\n", " ") + "}"
                elif c > 0:
                    if len(anno_str) > 0:
                        anno_str += "; "
                    anno_str += str(c) + "x " + anno
        return anno_str

    @gen.coroutine
    @without_document_lock
    def render(self, area, zoom_in_render):
        def unlocked_task():
            def cancelable_task():
                self.cancel_render = False
                if self.meta is None or self.idx is None:
                    self.curdoc.add_timeout_callback(
                        lambda: self.render_callback(), self.settings["interface"]["update_freq"]["val"]*1000)
                    return False
                    
                def callback():
                    self.spinner.css_classes = ["fade-in"]
                self.curdoc.add_next_tick_callback(callback)

                def power_of_ten(x):
                    if self.settings["interface"]["snap_bin_size"] == "no":
                        return math.ceil(x)
                    n = 0
                    while True:
                        for i in [1, 1.25, 2.5, 5]:
                            if i*10**n > x:
                                return i*10**n
                        n += 1
                def comp_bin_size():
                    t = self.settings["interface"]["min_bin_size"]["val"]
                    return max(1, math.ceil((1 + t % 9) * 10**(t // 9)) // self.meta.dividend)
                if self.settings["interface"]["bin_aspect_ratio"] == "view":
                    h_bin = power_of_ten( (area[2] - area[0]) / \
                                            math.sqrt(self.settings["interface"]["max_num_bins"]["val"] * 1000) )
                    h_bin = max(h_bin, comp_bin_size(), 1)
                    w_bin = power_of_ten( (area[3] - area[1]) / \
                                            math.sqrt(self.settings["interface"]["max_num_bins"]["val"] * 1000) )
                    w_bin = max(w_bin, comp_bin_size(), 1)
                elif self.settings["interface"]["bin_aspect_ratio"] == "coord":
                    area_bin = (area[2] - area[0]) * (area[3] - area[1]) / \
                                            (self.settings["interface"]["max_num_bins"]["val"] * 1000)
                    h_bin = power_of_ten(math.sqrt(area_bin))
                    h_bin = max(h_bin, comp_bin_size(), 1)
                    w_bin = h_bin
                else:
                    raise RuntimeError("invlaid square_bins_d value")

                if self.last_h_w_bin == (h_bin, w_bin) and zoom_in_render:
                    self.curdoc.add_timeout_callback(
                        lambda: self.render_callback(), self.settings["interface"]["update_freq"]["val"]*1000)
                    return True
                self.last_h_w_bin = (h_bin, w_bin)
                self.last_drawing_area = area

                area[0] -= area[0] % w_bin # align to nice and even number
                area[1] -= area[1] % h_bin # align to nice and even number
                area[2] += w_bin - (area[2] % w_bin) # align to nice and even number
                area[3] += h_bin - (area[3] % h_bin) # align to nice and even number

                if self.do_export == "full":
                    area[0] = 0
                    area[1] = 0
                    area[2] = self.meta.chr_sizes.chr_start_pos["end"]
                    area[3] = self.meta.chr_sizes.chr_start_pos["end"]

                print("bin_size", int(h_bin), "x", int(w_bin), "\033[K")
                xx = self.bin_coords(area, h_bin, w_bin)
                if self.cancel_render:
                    return
                bin_coords, bin_cols, bin_rows, bin_coords_2, _, _, bin_coords_3, _, _ = xx
                bins = self.make_bins(bin_coords)
                if self.cancel_render:
                    return
                flat = self.flatten_bins(bins)
                norm_ddd_out = self.norm_ddd(flat, bin_coords_2)
                norm = self.norm_bins(w_bin, norm_ddd_out, bin_cols, bin_rows)
                if self.cancel_render:
                    return
                sym = self.bin_symmentry(h_bin, norm, bin_coords, bin_cols, bin_rows)
                if self.cancel_render:
                    return
                c = self.color_bins(sym)
                b_col = self.color((MAP_Q_MAX-1) //
                                2) if self.settings['replicates']['between_group'] == "sub" else self.color(0)
                purged, purged_coords, purged_coords_2, purged_sym, purged_flat_a, purged_flat_b = \
                    self.purge(b_col, c, bin_coords_3, bin_coords_2,
                            self.color_bins_a(sym), *flat)

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
                }
                
                best_bins = [(None,0,0)]*3
                for cc, a, b in zip(d_heatmap["s"], d_heatmap["d_a"], d_heatmap["d_b"]):
                    c = self.color_bins_c(cc)/255
                    for idx, x in enumerate([0.1, 0.5, 0.9]):
                        if best_bins[idx][0] is None or abs(c-x) < abs(best_bins[idx][0]-x):
                            best_bins[idx] = (c, a, b)

                color_bar_ticks = []
                color_bar_tick_labels = []
                for c, a, b in best_bins:
                    if not c is None:
                        color_bar_ticks.append(c)
                        color_bar_tick_labels.append(str(round(c, 2)) + ": " + str(round(a, 2)) + "/" + 
                                                     str(round(b, 2)))

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

                raw_data_x = {
                    "xs": [x_pos for _ in range(x_num_raw)],
                    "chr": [x_chr for _ in range(x_num_raw)],
                    "pos1": [x_pos1 for _ in range(x_num_raw)],
                    "pos2": [x_pos2 for _ in range(x_num_raw)],
                    "ys": [double_up(raw_x_heat), double_up(raw_x_norm_combined)] + x_ys,
                    "ls": ["heatmap row sum", "combined normalization"] + self.norm_x,
                    "cs": [Colorblind2[idx % 8] for idx in range(x_num_raw)],
                }
                raw_data_y = {
                    "xs": [y_pos for _ in range(y_num_raw)],
                    "chr": [y_chr for _ in range(y_num_raw)],
                    "pos1": [y_pos1 for _ in range(y_num_raw)],
                    "pos2": [y_pos2 for _ in range(y_num_raw)],
                    "ys": [double_up(raw_y_heat), double_up(raw_y_norm_combined)] + y_ys,
                    "ls": ["heatmap col sum", "combined normalization"] + self.norm_y,
                    "cs": [Colorblind2[idx % 8] for idx in range(y_num_raw)],
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
                    xx = self.bin_rows(area, w_bin, filter_l=[])
                    if self.cancel_render:
                        return
                    bin_rows_unfiltr, bin_rows_2_unfiltr, bin_rows_3_unfiltr = xx
                    for idx, anno in enumerate(self.displayed_annos[::-1]):
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
                                d_anno_x["c"].append(Colorblind2[idx % 8])
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
                    xx = self.bin_cols(area, h_bin, filter_l=[])
                    if self.cancel_render:
                        return
                    bin_cols_unfiltr, bin_cols_2_unfiltr, bin_cols_3_unfiltr = xx
                    for idx, anno in enumerate(self.displayed_annos[::-1]):
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
                                d_anno_y["c"].append(Colorblind2[idx % 8])
                                if x > 10:
                                    d_anno_y["info"].append("n/a")
                                else:
                                    d_anno_y["info"].append(self.meta.annotations[anno].info(s, s+e))

                self.render_step_log("transfer_data")

                @gen.coroutine
                def callback():
                    self.curdoc.hold()
                    if self.settings['replicates']['between_group'] == "sub":
                        palette = [xxx/50 - 1 for xxx in range(100)]
                    else:
                        palette = [xxx/100 for xxx in range(100)]
                    self.color_mapper.palette = self.color_bins_b(palette)
                    self.color_info.formatter.args = {"ticksx": color_bar_ticks, "labelsx": color_bar_tick_labels}
                    self.color_info.ticker.ticks = color_bar_ticks
                    self.color_info.visible = False
                    self.color_info.visible = True # trigger re-render
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
                        if len(self.displayed_annos) == 0:
                            self.anno_x.x_range.factors = [""]
                            self.anno_y.y_range.factors = [""]
                        else:
                            self.anno_x.x_range.factors = self.displayed_annos
                            self.anno_y.y_range.factors = self.displayed_annos

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
                            ra.top = area[3] if top is None else top
                            if not color is None:
                                ra.fill_color = color

                        set_bounds(self.raw_x, left=mmin(*raw_x_heat, *raw_x_norm_combined), 
                                    right=mmax(*raw_x_heat, *raw_x_norm_combined))
                        set_bounds(self.ratio_x, left=0, right=mmax(*raw_x_ratio))
                        set_bounds(self.raw_y, bottom=mmin(*raw_y_heat, *raw_y_norm_combined),
                                    top=mmax(*raw_y_heat, *raw_y_norm_combined))
                        set_bounds(self.ratio_y, bottom=0, top=mmax(*raw_y_ratio))
                        set_bounds(self.anno_x, left=0, right=len(self.displayed_annos))
                        set_bounds(self.anno_y, bottom=0, top=len(self.displayed_annos))

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
                    total_time, ram_usage = self.render_done(len(bins[0]) if len(bins) > 0 else 0)
                    self.curr_bin_size.text = end_text + "<br>Took " + str(total_time) + " in total.<br>" + str(ram_usage) + "% RAM used.<br> " + str(len(bins[0])//1000) if len(bins) > 0 else "0" + "k bins rendered."
                    self.curdoc.add_timeout_callback(
                        lambda: self.render_callback(), self.settings["interface"]["update_freq"]["val"]*1000)

                if not self.do_export is None:
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

                self.curdoc.add_next_tick_callback(callback)
                return True
            while cancelable_task() is None:
                pass
            def callback():
                self.spinner.css_classes = ["fade-out"]
            self.curdoc.add_next_tick_callback(callback)

        yield executor.submit(unlocked_task)

    def setup_coordinates(self):
        self.meta.setup_coordinates(self, FigureMaker.x_coords_d,  FigureMaker.y_coords_d)
        FigureMaker().update_visibility()

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
                    self.settings["interface"]["min_bin_size"]["val"] = self.min_max_bin_size.value
                    self.min_max_bin_size.value = max(9*2, to_idx(self.meta.dividend))
                    self.setup_coordinates()
                    self.idx = Tree_4(self.meta_file.value)
                    self.idx_norm = Tree_3(self.meta_file.value)
                    print("done loading\033[K")
                    self.trigger_render()
                    self.curr_bin_size.text = "done loading"
                else:
                    print("File not found")
                    self.curr_bin_size.text = "File not found. <br>Waiting for Fileinput."
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
                min_change = 1-self.settings["interface"]["zoom_redraw"]["val"]/100
                zoom_in_render = False
                # print(overlap)
                if curr_area_size / self.curr_area_size < min_change or self.force_render or \
                        MainLayout.area_outside(self.last_drawing_area, curr_area):
                    if curr_area_size / self.curr_area_size < min_change:
                        self.new_render("zoom in")
                        zoom_in_render = True
                    elif self.force_render:
                        self.new_render("new setting")
                    elif MainLayout.area_outside(self.last_drawing_area, curr_area):
                        self.new_render("pan / zoom out")
                    else:
                        self.new_render("program start")
                    self.force_render = False
                    self.curr_area_size = curr_area_size
                    x = self.settings["interface"]["add_draw_area"]["val"]/100
                    new_area = [curr_area[0] - w*x, curr_area[1] - h*x,
                                curr_area[2] + w*x, curr_area[3] + h*x]

                    def callback():
                        self.render(new_area, zoom_in_render)
                    self.curdoc.add_next_tick_callback(callback)
                    return

            self.curdoc.add_timeout_callback(
                lambda: self.render_callback(), self.settings["interface"]["update_freq"]["val"]*1000)

    def set_root(self):
        self.curdoc.clear()
        self.curdoc.add_root(self.root)
        self.curdoc.title = "Smoother"
        self.do_render = True
        self.force_render = True

        self.render_callback()
