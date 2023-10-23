from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, Range1d
from bokeh.models.tools import ToolbarBox, ProxyToolbar
import math

FONT = "Consolas, sans-serif"
DROPDOWN_HEIGHT = 30


class FigureMaker:
    def __init__(self):
        self.args = {}
        self.x_axis_visible = False
        self.y_axis_visible = False
        self.toolbar_list = None
        self._hide_on = []
        self.x_axis_label_orientation = None
        self.y_axis_label_orientation = None
        self.y_axis_label = ""
        self.x_axis_label = ""
        self._range1d = False
        self.no_border_h = False
        self.no_border_v = False
        self.is_hidden = False

    def get(self, register):
        ret = figure(tools="pan,wheel_zoom,box_zoom", **self.args)
        ret.x(x=1, y=1, line_color=None)
        ret.xaxis.visible = self.x_axis_visible
        ret.yaxis.visible = self.y_axis_visible
        ret.yaxis.axis_label = self.y_axis_label
        ret.xaxis.axis_label = self.x_axis_label
        if not self.toolbar_list is None:
            self.toolbar_list.append(ret.toolbar)
            ret.toolbar_location = None
        if len(self._hide_on) > 0:
            register.hidable_plots.append((ret, self._hide_on))
        if not self.x_axis_label_orientation is None:
            ret.xaxis.major_label_orientation = self.x_axis_label_orientation
        if not self.y_axis_label_orientation is None:
            ret.yaxis.major_label_orientation = self.y_axis_label_orientation
        if self._range1d:
            ret.x_range = Range1d()
            ret.y_range = Range1d()
        ret.min_border_left = 0
        ret.min_border_bottom = 0
        if self.no_border_h:
            ret.min_border_right = 0
        if self.no_border_v:
            ret.min_border_top = 0
        ret.xaxis.axis_label_text_font_size = "11px"
        ret.yaxis.axis_label_text_font_size = "11px"
        ret.xaxis.axis_label_standoff = 0
        ret.yaxis.axis_label_standoff = 0
        ret.xaxis.major_label_text_font = FONT
        ret.yaxis.major_label_text_font = FONT
        ret.xaxis.axis_label_text_font = FONT
        ret.yaxis.axis_label_text_font = FONT
        ret.title.text_font = FONT
        ret.xgrid.level = "glyph"
        ret.ygrid.level = "glyph"
        ret.background_fill_color = "lightgrey"
        render_area = BoxAnnotation(fill_alpha=1, fill_color="white", level="image")
        ret.add_layout(render_area)
        if self.is_hidden:
            ret.visible = False
        register.render_areas[ret] = render_area
        register.grid_line_plots.append(ret)
        return ret

    def name(self, name):
        self.args["name"] = name
        return self

    def range1d(self):
        self._range1d = True
        return self

    def w(self, w):
        self.args["width"] = w
        return self

    def h(self, h):
        self.args["height"] = h
        return self

    def frame_h(self, h):
        self.args["frame_height"] = h
        return self

    def link_y(self, other):
        self.args["x_range"] = (0, 1)
        self.args["y_range"] = other.y_range
        # self.args["sizing_mode"] = "stretch_height"
        self.args["height_policy"] = "max"
        self.args["height"] = 10
        self.no_border_v = True
        return self

    def link_x(self, other):
        self.args["x_range"] = other.x_range
        self.args["y_range"] = (0, 1)
        # self.args["sizing_mode"] = "stretch_width"
        self.args["width_policy"] = "max"
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

    def scale(self):
        self.args["sizing_mode"] = "scale_height"
        self.args["height"] = 10
        self.args["width"] = 10
        self.no_border_h = True
        self.no_border_v = True
        return self

    def log_x(self):
        self.args["x_axis_type"] = "log"
        return self

    def log_y(self):
        self.args["y_axis_type"] = "log"
        return self

    def _axis_of(self, other, register, hide_keyword):
        self.hide_on(hide_keyword, register)
        for plot, _hide_on in register.hidable_plots:
            if plot == other:
                for key in _hide_on:
                    self.hide_on(key, register)

    def x_axis_of(
        self,
        other,
        register,
        label="",
        stretch=False,
        flip_orientation=True,
        hide_keyword="axis",
    ):
        self._axis_of(other, register, hide_keyword)

        self.x_axis_visible = True
        self.args["x_range"] = other.x_range
        self.args["frame_height"] = 1
        if stretch:
            self.args["sizing_mode"] = "stretch_width"
            # self.args["width_policy"] = "fit"
            self.w(None)
        else:
            self.w(other.width)
            self.args["sizing_mode"] = "fixed"
        self.args["align"] = "start"
        if flip_orientation:
            self.x_axis_label_orientation = math.pi / 2
        self.x_axis_label = label
        self.no_border_v = True
        return self

    def y_axis_of(
        self,
        other,
        register,
        label="",
        stretch=False,
        flip_orientation=False,
        hide_keyword="axis",
    ):
        self._axis_of(other, register, hide_keyword)

        self.y_axis_visible = True
        self.args["y_range"] = other.y_range
        self.args["frame_width"] = 1
        if stretch:
            self.args["sizing_mode"] = "stretch_height"
            # self.args["height_policy"] = "max"
            self.h(None)
        else:
            self.h(other.height)
            self.args["sizing_mode"] = "fixed"
        self.args["align"] = "end"
        if flip_orientation:
            self.y_axis_label_orientation = math.pi / 2
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

    def combine_tools(self, toolbar_list):
        self.toolbar_list = toolbar_list
        return self

    def hide_on(self, key, register):
        if not key in register.show_hide:
            register.show_hide[key] = not self.is_hidden
        self._hide_on.append(key)
        return self

    @staticmethod
    def get_tools(tools_list, toolbar_location="above", **toolbar_options):
        tools = sum([toolbar.tools for toolbar in tools_list], [])
        proxy = ProxyToolbar(
            toolbars=tools_list, tools=tools, **toolbar_options, name="toolbar"
        )
        proxy.logo = None
        return ToolbarBox(toolbar=proxy, toolbar_location=toolbar_location)
