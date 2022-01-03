from bokeh.layouts import grid, row, column
from bokeh.plotting import figure, curdoc
from bokeh.models.tools import ToolbarBox, ProxyToolbar
from bokeh.models import Dropdown, Button, RangeSlider, Slider
import math
from datetime import datetime
from tornado import gen
from bokeh.document import without_document_lock
from bokeh.models import Panel, Tabs

SETTINGS_WIDTH = 200

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

    def get(self):
        ret = figure(**self.args)
        ret.x(x=0, y=0)
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
        return ret

    def w(self, w):
        self.args["frame_width"] = w
        return self

    def h(self, h):
        self.args["frame_height"] = h
        return self

    def link_y(self, other):
        self.args["y_range"] = other.y_range
        self.args["sizing_mode"] = "stretch_height"
        self.args["height"] = 10
        return self

    def link_x(self, other):
        self.args["x_range"] = other.x_range
        self.args["sizing_mode"] = "stretch_width"
        self.args["width"] = 10
        return self

    def stretch(self):
        self.args["sizing_mode"] = "stretch_both"
        self.args["height"] = 10
        self.args["width"] = 10
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
        else:
            self.w(other.frame_width)
            self.args["sizing_mode"] = "fixed"
        self.args["width"] = 10
        self.args["align"] = "start"
        self.x_axis_label_orientation = math.pi/4
        self.x_axis_label = label
        return self

    def y_axis_of(self, other, label=""):
        self._axis_of(other)

        self.y_axis_visible = True
        self.args["y_range"] = other.y_range
        self.args["frame_width"] = 1
        if other.sizing_mode in ["stretch_both", "stretch_height"]:
            self.args["sizing_mode"] = "stretch_height"
        else:
            self.h(other.frame_height)
            self.args["sizing_mode"] = "fixed"
        self.args["height"] = 10
        self.args["align"] = "end"
        self.y_axis_label = label
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

def dropdown_select(title, event, *options):
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
    ret.on_click(_event)
    return ret



class MainLayout:
    def __init__(self):
        self.do_render = False
        self.curdoc = curdoc()
        self.last_drawing_area = (0,0,0,0)

        global SETTINGS_WIDTH
        tollbars = []
        self.heaptmap = FigureMaker().stretch().combine_tools(tollbars).get()
        self.heaptmap_x_axis = FigureMaker().x_axis_of(self.heaptmap, "DNA").combine_tools(tollbars).get()
        self.heaptmap_y_axis = FigureMaker().y_axis_of(self.heaptmap, "RNA").combine_tools(tollbars).get()

        self.ratio_x = FigureMaker().w(100).link_y(self.heaptmap).hide_on("ratio").combine_tools(tollbars).get()
        self.ratio_x_axis = FigureMaker().x_axis_of(self.ratio_x).combine_tools(tollbars).get()

        self.ratio_y = FigureMaker().h(100).link_x(self.heaptmap).hide_on("ratio").combine_tools(tollbars).get()
        self.ratio_y_axis = FigureMaker().y_axis_of(self.ratio_y).combine_tools(tollbars).get()

        self.raw_x = FigureMaker().w(100).link_y(self.heaptmap).hide_on("raw").combine_tools(tollbars).get()
        self.raw_x_axis = FigureMaker().x_axis_of(self.raw_x).combine_tools(tollbars).get()

        self.raw_y = FigureMaker().h(100).link_x(self.heaptmap).hide_on("raw").combine_tools(tollbars).get()
        self.raw_y_axis = FigureMaker().y_axis_of(self.raw_y).combine_tools(tollbars).get()

        self.anno_x = FigureMaker().w(100).link_y(self.heaptmap).hide_on("annotation").combine_tools(tollbars).get()
        self.anno_x_axis = FigureMaker().x_axis_of(self.anno_x).combine_tools(tollbars).get()

        self.anno_y = FigureMaker().h(100).link_x(self.heaptmap).hide_on("annotation").combine_tools(tollbars).get()
        self.anno_y_axis = FigureMaker().y_axis_of(self.anno_y).combine_tools(tollbars).get()

        tool_bar = FigureMaker.get_tools(tollbars)
        SETTINGS_WIDTH = tool_bar.width
        show_hide = FigureMaker.show_hide_dropdown(("Axes", "axis"), ("Ratio", "ratio"), ("Raw", "raw"),
                                                   ("Annotations", "annotation"), ("Tools", "tools"))

        replicates = dropdown_select("Replicates", lambda _: None,
                        ("Show Minimium", "min"), ("Show Sum", "sum"))
        symmetrie = dropdown_select("Symmetry", lambda _: None,
                        ("Show All", "all"), ("Only Show Symmetric", "sym"), ("Only Show Asymmetric", "asym"))
        normalization = dropdown_select("Normalize by", lambda _: None,
                        ("Largest Bin Overall", "max_bin_global"), ("Largest Visible Bin", "max_bin_visible"),
                        ("Number of Reads", "num_reads"), ("Column", "column"), ("Coverage", "tracks"))

        mapq_slider = RangeSlider(width=SETTINGS_WIDTH, start=0, end=255, value=(0,255), step=1,
                                  title="Mapping Quality Bounds")
        mapq_slider.sizing_mode = "fixed"

        interactions_bounds_slider = Slider(width=SETTINGS_WIDTH, start=1, end=1000, value=1, step=1,
                                  title="Color Scale Begin")
        interactions_bounds_slider.sizing_mode = "fixed"

        interactions_slider = Slider(width=SETTINGS_WIDTH, start=1, end=1.1, value=1.06, step=0.001,
                                  title="Color Scale Log Base", format="0[.]000")
        interactions_slider.sizing_mode = "fixed"

        self.update_frequency_slider = Slider(width=SETTINGS_WIDTH, start=0.1, end=3, value=2, step=0.1,
                                  title="Update Frequency [seconds]", format="0[.]000")
        self.update_frequency_slider.sizing_mode = "fixed"

        self.redraw_slider = Slider(width=SETTINGS_WIDTH, start=0, end=100, value=10, step=1,
                                  title="Redraw if [%] of shown area changed")
        self.redraw_slider.sizing_mode = "fixed"

        #FigureMaker.toggle_hide("axis")
    
        _settings = Tabs(
            tabs=[
                Panel(child=column([tool_bar, show_hide, replicates, symmetrie]), title="General"),
                Panel(child=column([normalization, mapq_slider, interactions_bounds_slider, interactions_slider]), title="Normalization"),
                Panel(child=column([self.update_frequency_slider, self.redraw_slider]), title="Advanced"),
            ],
            sizing_mode="stretch_height"
        )

        FigureMaker._hidable_plots.append((_settings, ["tools"]))
        settings = row([_settings, FigureMaker.reshow_settings()], sizing_mode="stretch_height")

        grid_layout = [
[self.heaptmap_y_axis, self.anno_x,   self.raw_x,      self.ratio_x,      None,              self.heaptmap,   settings],
[None,              self.anno_x_axis, self.raw_x_axis, self.ratio_x_axis, None,              None,               None],
[None,              None,             None,            None,              self.ratio_y_axis, self.ratio_y,       None],
[None,              None,             None,            None,              self.raw_y_axis,   self.raw_y,         None],
[None,              None,             None,            None,              self.anno_y_axis,  self.anno_y,        None],
[None,              None,             None,            None,              None,            self.heaptmap_x_axis, None],
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

    def render(self, area):
        pass

    def render_callback(self):
        if self.do_render:
            if not None in (self.heaptmap.x_range.start, self.heaptmap.x_range.end, self.heaptmap.y_range.start, self.heaptmap.y_range.end):
                curr_area = (self.heaptmap.x_range.start, self.heaptmap.y_range.start, 
                                self.heaptmap.x_range.end, self.heaptmap.y_range.end)
                overlap = MainLayout.area_overlap(self.last_drawing_area, curr_area)
                min_change = self.redraw_slider.value/100
                print(overlap)
                if 1-overlap >= min_change:
                    print("render!", datetime.now().strftime("%H:%M:%S"))
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
        self.render_callback()
