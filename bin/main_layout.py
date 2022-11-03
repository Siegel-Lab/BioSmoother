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
import os
import sys
#from bin.heatmap_as_r_tree import *
from bokeh.palettes import Viridis256, Colorblind, Plasma256, Turbo256
from datetime import datetime, timedelta
import psutil
from concurrent.futures import ThreadPoolExecutor
from bokeh.models import BoxAnnotation
from bokeh.models.tickers import AdaptiveTicker
from bin.libContactMapping import Quarry
from bin.render_step_logger import *
import json
import shutil
from bin.figure_maker import FigureMaker, DROPDOWN_HEIGHT
from bin.extra_ticks_ticker import *

SETTINGS_WIDTH = 400
DEFAULT_SIZE = 50
ANNOTATION_PLOT_NAME = "Annotation"
RATIO_PLOT_NAME = "Ratio"
RAW_PLOT_NAME = "Cov"

DIV_MARGIN = (5, 5, 0, 5)
BTN_MARGIN = (3, 3, 3, 3)
BTN_MARGIN_2 = (3, 3, 3, 3)

CONFIG_FILE_VERSION = 0.1

executor = ThreadPoolExecutor(max_workers=1)


## @todo use multi-inheritance to split this class into smaller ones


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
            if not active_item is None:
                event(active_item)

        def _event(e):
            for _, key in options:
                d[key] = False
            d[e.item] = True
            event(e.item)
            make_menu()
        ret.on_click(_event)
        return ret, set_menu

    def dropdown_select(self, title, tooltip, *options, active_item=None, event=None):
        if event is None:
            def default_event(e):
                self.session.set_value(active_item, e)
                self.trigger_render()
            event = default_event
        ret, set_menu = self.dropdown_select_h(title, event, tooltip)
        if not active_item is None:
            self.dropdown_select_config.append((lambda x: set_menu([*options], x), active_item))
        else:
            set_menu(options)
        return ret

    def dropdown_select_session(self, title, tooltip, session_key, active_item, add_keys=[], event=None):
        if event is None:
            def default_event(e):
                self.session.set_value(active_item, e)
                self.trigger_render()
            event = default_event
        ret, set_menu = self.dropdown_select_h(title, event, tooltip)
        def set_menu_2(x):
            set_menu(add_keys + [(x,x) for x in self.session.get_value(session_key)], x)
        self.dropdown_select_config.append((set_menu_2, active_item))
        return ret

    def multi_choice(self, label, checkboxes, session_key=None, callback=None, orderable=True):
        if callback is None:
            def default_callback(n, cb):
                for v in cb.values():
                    self.session.set_value(v[0], v[1])
                if not session_key is None:
                    self.session.set_value(session_key, n)
                self.trigger_render()
            callback = default_callback
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
            Div(text="<br>".join(y for _, y in checkboxes), css_classes=["vertical"], sizing_mode="fixed", 
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
            for k, n in checkboxes:
                cb[n] = (k, [])
            order = []
            for n, opts in self.reset_options[label][1]:
                order.append(n)
                for opt in opts:
                    cb[checkboxes[opt][1]][1].append(n)
            callback(order, cb)

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
                    if n in active_dict[cb[1]]:
                        self.reset_options[label][1][jdx][1].append(idx)
            reset_event(0)
            trigger_callback()

        return set_options, layout
    
    
    def multi_choice_auto(self, label, checkboxes, session_key, callback=None, orderable=True):
        set_options, layout = self.multi_choice(label, checkboxes, session_key, callback, orderable)
        self.multi_choice_config.append((set_options, session_key, checkboxes))
        return layout

    def config_row(self, file_nr, callback=None, lock_name=False):
        SYM_WIDTH = 10
        SYM_CSS = ["other_button"]
        with open('smoother/static/conf/' + str(file_nr) + '.json', 'r') as f:
            settings = json.load(f)
        with open('smoother/static/conf/factory_' + str(file_nr) + '.json', 'r') as f:
            factory_default = json.load(f)

        if CONFIG_FILE_VERSION != settings["smoother_config_file_version"]:
            print("Config file version does not match: expected", CONFIG_FILE_VERSION, 
                  "but got", settings["smoother_config_file_version"])
        
        name = TextInput(value=settings["display_name"], sizing_mode="stretch_width", disabled=lock_name)
        apply_button = Button(label="", css_classes=SYM_CSS + ["fa_apply"], width=SYM_WIDTH, 
                            height=SYM_WIDTH, sizing_mode="fixed", button_type="light", align="center")
        save_button = Button(label="", css_classes=SYM_CSS + ["fa_save"], width=SYM_WIDTH, 
                            height=SYM_WIDTH, sizing_mode="fixed", button_type="light", align="center")
        reset_button = Button(label="", 
                        css_classes=SYM_CSS + ["fa_reset"] if settings != factory_default else ["fa_reset_disabled"], 
                            width=SYM_WIDTH, 
                            height=SYM_WIDTH, sizing_mode="fixed", button_type="light", align="center",
                            disabled=settings == factory_default)
        def save_event():
            def dict_diff(a, b):
                r = {}
                for k in a.keys():
                    if isinstance(a[k], dict):
                        d = dict_diff(a[k], b[k])
                        if len(d) > 0:
                            r[k] = d
                    elif k not in b or a[k] != b[k]:
                        r[k] = a[k]
                return r
            print("saving...")
            settings = dict_diff(self.session.get_value(["settings"]), self.settings_default)
            settings["display_name"] = name.value
            settings["smoother_config_file_version"] = CONFIG_FILE_VERSION
            with open('smoother/static/conf/' + str(file_nr) + '.json', 'w') as f:
                json.dump(settings, f)
            reset_button.disabled = settings == factory_default
            reset_button.css_classes = SYM_CSS + ["fa_reset"] if settings != factory_default else ["fa_reset_disabled"]
            print("saved")
        save_button.on_click(lambda _: save_event())

        def reset_event():
            shutil.copyfile('smoother/static/conf/factory_' + str(file_nr) + '.json', 
                            'smoother/static/conf/' + str(file_nr) + '.json')
            reset_button.disabled = True
            reset_button.css_classes = SYM_CSS + ["fa_reset_disabled"]
            with open('smoother/static/conf/' + str(file_nr) + '.json', 'r') as f:
                settings = json.load(f)
            name.value = settings["display_name"]
        reset_button.on_click(lambda _: reset_event())

        def apply_event():
            print("applying...")
            with open('smoother/static/conf/' + str(file_nr) + '.json', 'r') as f:
                settings = json.load(f)
            def combine_dict(a, b):
                r = {}
                for k in b.keys():
                    if isinstance(b[k], dict) and k in a:
                        r[k] = combine_dict(a[k], b[k])
                    elif isinstance(b[k], dict):
                        r[k] = b[k]
                    elif k in a:
                        r[k] = a[k]
                    else:
                        r[k] = b[k]
                return r
            self.session.set_value(["settings"], combine_dict(settings, self.session.get_value(["settings"])))
            self.curdoc.hold()
            self.do_config()
            self.curdoc.unhold()
            self.trigger_render()
            print("applied")
        apply_button.on_click(lambda _: apply_event())

        return row([name, apply_button, save_button, reset_button], sizing_mode="stretch_width")

    def make_slider_spinner(self, title, settings, width=200, 
                            on_change=None, spinner_width=80, sizing_mode="stretch_width"):
        if on_change is None:
            def default_on_change(val):
                self.session.set_value(settings + ["val"], val)
                self.trigger_render()
            on_change = default_on_change
        spinner = Spinner(width=spinner_width)
        slider = Slider(title=title, show_value=False, width=width-spinner_width, sizing_mode=sizing_mode,
                        start=0, end=1, value=0)

        spinner.js_link("value", slider, "value")
        slider.js_link("value", spinner, "value")
        slider.on_change("value_throttled", lambda _x,_y,_z: on_change(slider.value))
        spinner.on_change("value_throttled", lambda _x,_y,_z: on_change(spinner.value))

        self.slider_spinner_config.append((slider, spinner, on_change, settings))

        return row([slider, spinner], width=width, margin=DIV_MARGIN)

    def make_range_slider_spinner(self, title, settings, width=200, 
                            on_change=None, spinner_width=80, sizing_mode="stretch_width"):
        if on_change is None:
            def default_on_change(val):
                self.session.set_value(settings + ["val_min"], val[0])
                self.session.set_value(settings + ["val_max"], val[1])
                self.trigger_render()
            on_change = default_on_change
        slider = RangeSlider(title=title, show_value=False, width=width-spinner_width*2, sizing_mode=sizing_mode,
                        start=0, end=1, value=(0,1))
        spinner_start = Spinner(width=spinner_width)
        spinner_end = Spinner(width=spinner_width)

        spinner_start.js_on_change('value', CustomJS(args=dict(other=slider), 
                                    code="other.value = [this.value, other.value[1]]" ) )
        slider.js_link("value", spinner_start, "value", attr_selector=0)

        spinner_end.js_on_change('value', CustomJS(args=dict(other=slider), 
                                    code="other.value = [other.value[0], this.value]" ) )
        slider.js_link("value", spinner_end, "value", attr_selector=1)

        slider.on_change("value_throttled", lambda _x,_y,_z: on_change(slider.value))
        spinner_end.on_change("value_throttled", lambda _x,_y,_z: on_change(slider.value))
        spinner_start.on_change("value_throttled", lambda _x,_y,_z: on_change(slider.value))

        self.range_slider_spinner_config.append((slider, spinner_start, spinner_end, on_change, settings))

        return row([slider, spinner_start, spinner_end], width=width, margin=DIV_MARGIN)

    def make_checkbox(self, title, tooltip="", settings=[], on_change=None, width=200):
        div = Div(text=title, sizing_mode="stretch_width")
        cg = CheckboxGroup(labels=[""], sizing_mode="fixed", width=20)
        if on_change is None:
            def default_event(active):
                self.session.set_value(settings, active)
                self.trigger_render()
            on_change = default_event
        cg.on_change("active", lambda _1,_2,_3: on_change(0 in cg.active))

        self.checkbox_config.append((cg, settings))

        return row([div, cg], width=width, margin=DIV_MARGIN)

    def config_slider_spinner(self):
        for slider, spinner, on_change, session_key in self.slider_spinner_config:
            value = self.session.get_value(session_key + ["val"])
            start = self.session.get_value(session_key + ["min"])
            end = self.session.get_value(session_key + ["max"])
            step = self.session.get_value(session_key + ["step"])
            
            spinner_min = self.session.get_value(session_key + ["spinner_min_restricted"])
            spinner_max = self.session.get_value(session_key + ["spinner_max_restricted"])
            
            if spinner_min:
                spinner.low = start
            else:
                spinner.low = None
            if spinner_max:
                spinner.high = end
            else:
                spinner.high = None
            spinner.value = value
            spinner.step = step

            slider.start = start
            slider.end = end
            slider.value = value
            slider.step = step

            on_change(value)

    def config_range_slider_spinner(self):
        for slider, spinner_start, spinner_end, on_change, session_key in self.range_slider_spinner_config:
            value_min = self.session.get_value(session_key + ["val_min"])
            value_max = self.session.get_value(session_key + ["val_max"])
            start = self.session.get_value(session_key + ["min"])
            end = self.session.get_value(session_key + ["max"])
            step = self.session.get_value(session_key + ["step"])

            spinner_min = self.session.get_value(session_key + ["spinner_min_restricted"])
            spinner_max = self.session.get_value(session_key + ["spinner_max_restricted"])

            if spinner_min:
                spinner_start.low = start
            else:
                spinner_start.low = None
            if spinner_max:
                spinner_start.high = end
            else:
                spinner_start.high = None
            spinner_start.value = value_min
            spinner_start.step = step

            if spinner_min:
                spinner_end.low = start
            else:
                spinner_end.low = None
            if spinner_max:
                spinner_end.high = end
            else:
                spinner_end.high = None
            spinner_end.value = value_max
            spinner_end.step = step

            slider.start = start
            slider.end = end
            slider.value = [value_min, value_max]
            slider.step = step

            on_change([value_min, value_max])

    def config_dropdown(self):
        for set_menu, session_key in self.dropdown_select_config:
            set_menu(self.session.get_value(session_key))

    def config_checkbox(self):
        for cg, session_key in self.checkbox_config:
            cg.active = [0] if self.session.get_value(session_key) else []

    def config_multi_choice(self):
        for set_options, session_key, checkboxes in self.multi_choice_config:
            ele_list = self.session.get_value(session_key)
            d = {}
            for key, name in checkboxes:
                d[name] = [ele for ele in ele_list if ele in self.session.get_value(key)] 
            set_options(ele_list, d)

    def do_config(self):
        
        def to_idx(x):
            if x <= 0:
                return 0
            power = int(math.log10(x))
            return 9*power+math.ceil(x / 10**power)-1

        min_ = max(to_idx(self.session.get_value(["dividend"])), 
                          self.session.get_value(["settings", "interface", "min_bin_size", "min"]))
        val_ = max(to_idx(self.session.get_value(["dividend"])), 
                          self.session.get_value(["settings", "interface", "min_bin_size", "val"]))

        self.session.set_value(["settings", "interface", "min_bin_size", "min"], min_)
        self.session.set_value(["settings", "interface", "min_bin_size", "val"], val_)

        self.min_max_bin_size.start = self.session.get_value(["settings", "interface", "min_bin_size", "min"])
        self.min_max_bin_size.end = self.session.get_value(["settings", "interface", "min_bin_size", "max"])
        self.min_max_bin_size.value = self.session.get_value(["settings", "interface", "min_bin_size", "val"])
        self.min_max_bin_size.step = self.session.get_value(["settings", "interface", "min_bin_size", "step"])

        self.undo_button.disabled = not self.session.has_undo()
        self.undo_button.css_classes = ["other_button", "fa_page_previous" if self.undo_button.disabled else "fa_page_previous_solid"]
        self.redo_button.disabled = not self.session.has_redo()
        self.redo_button.css_classes = ["other_button", "fa_page_next" if self.redo_button.disabled else "fa_page_next_solid"]

        self.heatmap.x_range.start = self.session.get_value(["area", "x_start"])
        self.heatmap.x_range.end = self.session.get_value(["area", "x_end"])
        self.heatmap.y_range.start = self.session.get_value(["area", "y_start"])
        self.heatmap.y_range.end = self.session.get_value(["area", "y_end"])


        self.config_slider_spinner()
        self.config_range_slider_spinner()
        self.config_dropdown()
        self.config_checkbox()
        self.config_multi_choice()

        self.low_color.color = self.session.get_value(["settings", "interface", "color_low"])
        self.high_color.color = self.session.get_value(["settings", "interface", "color_high"])

        self.config_show_hide(self.session.get_value(["settings", "interface", "show_hide"]))

        self.export_file.value = self.session.get_value(["settings", "export", "prefix"])


    def plot_render_area(self, plot):
        return self.render_areas[plot]

    def update_visibility(self):
        for plot, keys in self.hidable_plots:
            visible = True
            for key in keys:
                if not self.show_hide[key]:
                    visible = False
                    break
            if plot.visible != visible:
                plot.visible = visible
        if not self.unhide_button is None:
            if self.unhide_button.visible == self.show_hide["tools"]:
                self.unhide_button.visible = not self.show_hide["tools"]
        cx = "lightgrey" if self.show_hide["contig_borders"] else None
        cx2 = "lightgrey" if self.show_hide["grid_lines"] else None
        cy = "lightgrey" if self.show_hide["contig_borders"] else None
        cy2 = "lightgrey" if self.show_hide["grid_lines"] else None
        self.slope.line_color = "darkgrey" if self.show_hide["indent_line"] else None
        for plot in self.grid_line_plots:
            if plot.xgrid.grid_line_color != cx:
                plot.xgrid.grid_line_color = cx
            if plot.xgrid.minor_grid_line_color != cx2:
                plot.xgrid.minor_grid_line_color = cx2
            if plot.ygrid.grid_line_color != cy:
                plot.ygrid.grid_line_color = cy
            if plot.ygrid.minor_grid_line_color != cy2:
                plot.ygrid.minor_grid_line_color = cy2

    def toggle_hide(self, key):
        self.show_hide[key] = not self.show_hide[key]
        self.update_visibility()

    def is_visible(self, key):
        return self.show_hide[key]

    def make_show_hide_menu(self):
        menu = []
        for name, key in self.names:
            menu.append(
                (("☑ " if self.show_hide[key] or key == "tools" else "☐ ") + name, key))
        menu.append(
            (("☑ " if self.show_hide["grid_lines"] else "☐ ") + "Grid Lines", "grid_lines"))
        menu.append(
            (("☑ " if self.show_hide["indent_line"] else "☐ ") + "Identity Line", "indent_line"))
        menu.append(
            (("☑ " if self.show_hide["contig_borders"] else "☐ ") + "Contig Borders", "contig_borders"))
        return menu

    def make_show_hide_dropdown(self, session_key, *names):
        for _, key in names:
            if key not in self.show_hide:
                self.show_hide[key] = False
        self.names = names

        self.show_hide_dropdown = Dropdown(label="Show/Hide", menu=self.make_show_hide_menu(),
                       width=350, sizing_mode="fixed", css_classes=["other_button", "tooltip", "tooltip_show_hide"], height=DROPDOWN_HEIGHT)

        def event(e):
            self.toggle_hide(e.item)
            self.session.set_value(session_key + [e.item], not self.session.get_value(session_key + [e.item]))
            self.show_hide_dropdown.menu = self.make_show_hide_menu()
        self.show_hide_dropdown.on_click(event)
        return self.show_hide_dropdown

    def config_show_hide(self, settings):
        for key in self.show_hide.keys():
            self.show_hide[key] = settings[key]
        self.show_hide_dropdown.menu = self.make_show_hide_menu()
        self.update_visibility()


    def reshow_settings(self):
        self.unhide_button = Button(label="<", width=40, height=40, css_classes=["other_button"])
        self.unhide_button.sizing_mode = "fixed"
        self.unhide_button.visible = False

        def event(e):
            if self.session is not None:
                self.session.set_value(["settings", "interface", "show_hide", "tools"], True)
            self.toggle_hide("tools")
        self.unhide_button.on_click(event)
        return self.unhide_button

    def make_color_figure(self, palette):
        color_mapper = LinearColorMapper(palette=palette, low=0, high=1)
        color_figure = figure(tools='', height=0, width=350)
        color_figure.x(0,0)
        color_info = ColorBar(color_mapper=color_mapper, orientation="horizontal", 
                                   ticker=FixedTicker(ticks=[]), width=350)
        #color_info.formatter = FuncTickFormatter(
        #                args={"ticksx": [], "labelsx": []},
        #                code="""
        #                    for (let i = 0; i < ticksx.length; i++)
        #                        if(tick == ticksx[i])
        #                            return labelsx[i];
        #                    return "n/a";
        #                """)
        color_figure.add_layout(color_info, "below")

        # make plot invisible
        color_figure.axis.visible = False
        color_figure.toolbar_location = None
        color_figure.border_fill_alpha = 0
        color_figure.outline_line_alpha = 0

        return color_figure



    def __init__(self):
        self.show_hide = {"grid_lines": False, "contig_borders": True, "indent_line": False}
        self.hidable_plots = []
        self.grid_line_plots = []
        self.unhide_button = None
        self.render_areas = {}
        self.slope = None
        self.show_hide_dropdown = None
        self.names = None

        self.x_coords_d = "full_genome"
        self.y_coords_d = "full_genome"

        self.do_render = False
        self.force_render = True
        self.curdoc = curdoc()
        self.last_drawing_area = (0, 0, 0, 0)
        self.curr_area_size = 1
        self.render_logger = Logger()
        self.smoother_version = "?"
        self.reset_options = {}
        self.session = None
        with open('smoother/static/conf/default.json', 'r') as f:
            self.settings_default = json.load(f)

        self.heatmap = None
        d = {"screen_bottom": [], "screen_left": [], "screen_top": [], "screen_right": [], "color": [], 
             "chr_x": [], "chr_y": [], "index_left": [], "index_right": [],
             "index_bottom": [], "index_top": [], "score_total": [], "score_a": [], "score_b": [],
             "chr_x_symmetry" : [], "chr_y_symmetry" : [], "index_symmetry_left" : [], 
             "index_symmetry_right" : [], "index_symmetry_bottom" : [], "index_symmetry_top" : []}
        self.heatmap_data = ColumnDataSource(data=d)
        d = {"b": [], "l": [], "t": [], "r": []}
        self.overlay_data = ColumnDataSource(data=d)
        self.overlay_dataset_id = None
        self.heatmap_x_axis = None
        self.heatmap_y_axis = None
        self.raw_x = None
        self.raw_x_axis = None
        self.raw_y = None
        self.raw_y_axis = None
        d_x = {
            "chrs": [],
            "index_start": [],
            "index_end": [],
            "screen_pos": [],
            "values": [],
            "colors": [],
            "names": [],
        }
        d_y = {
            "chrs": [],
            "index_start": [],
            "index_end": [],
            "screen_pos": [],
            "values": [],
            "colors": [],
            "names": [],
        }
        self.raw_data_x = ColumnDataSource(data=d_x)
        self.raw_data_y = ColumnDataSource(data=d_y)
        self.anno_x = None
        self.anno_x_axis = None
        self.anno_y = None
        self.anno_y_axis = None
        d = {"anno_name": [], "screen_start": [], "screen_end": [], "color": [], "chr": [],
             "index_start": [], "index_end": [], "info": [], "num_anno": []}
        self.anno_x_data = ColumnDataSource(data=d)
        self.anno_y_data = ColumnDataSource(data=d)
        self.meta_file = None
        self.min_max_bin_size = None
        self.curr_bin_size = None
        self.spinner = None
        self.info_field = None
        self.do_export = None
        self.settings_row = None
        self.slider_spinner_config = []
        self.range_slider_spinner_config = []
        self.dropdown_select_config = []
        self.checkbox_config = []
        self.multi_choice_config = []
        self.export_file = None
        self.ticker_x = None
        self.ticker_y = None
        self.tick_formatter_x = None
        self.tick_formatter_y = None
        self.undo_button = None
        self.redo_button = None
        self.color_layout = None

        self.do_layout()

    def do_layout(self):

        global SETTINGS_WIDTH
        tollbars = []
        self.heatmap = FigureMaker().range1d().scale().combine_tools(tollbars).get(self)

        self.heatmap.quad(left="screen_left", bottom="screen_bottom", right="screen_right", top="screen_top", 
                          fill_color="color", line_color=None, source=self.heatmap_data, level="underlay")
        self.heatmap.xgrid.minor_grid_line_alpha = 0.5
        self.heatmap.ygrid.minor_grid_line_alpha = 0.5

        self.heatmap.quad(left="l", bottom="b", right="r", top="t", fill_color=None, line_color="red", 
                            source=self.overlay_data, level="underlay")

        self.overlay_dataset_id = Spinner(title="Overlay Lines Dataset Id", low=-1, step=1, value=-1, 
                                          width=DEFAULT_SIZE, mode="int")
        self.overlay_dataset_id.on_change("value_throttled", lambda x, y, z: self.trigger_render())


        self.heatmap.add_tools(HoverTool(
            tooltips=[
                ('(x, y)', "(@chr_x @index_left - @index_right, @chr_y @index_bottom - @index_top)"),
                ('sym(x, y)', "(@chr_x_symmetry @index_symmetry_left - @index_symmetry_right, @chr_y_symmetry @index_symmetry_bottom - @index_symmetry_top)"),
                ('score', "@score_total"),
                ('reads by group', "A: @score_a, B: @score_b")
            ]
        ))

        self.heatmap_x_axis = FigureMaker().x_axis_of(
            self.heatmap, self, "DNA", True).combine_tools(tollbars).get(self)
        self.heatmap_y_axis = FigureMaker().y_axis_of(
            self.heatmap, self, "RNA", True).combine_tools(tollbars).get(self)

        self.slope = Slope(gradient=1, y_intercept=0, line_color=None)
        self.heatmap.add_layout(self.slope)


        raw_hover_x = HoverTool(
            tooltips="""
                <div>
                    <span style="color: @colors">@names: $data_x</span>
                </div>
            """,
            mode='hline'
        )
        raw_hover_y = HoverTool(
            tooltips="""
                <div>
                    <span style="color: @colors">@names: $data_y</span>
                </div>
            """,
            mode='vline'
        )

        self.raw_x = FigureMaker().w(DEFAULT_SIZE).link_y(
            self.heatmap).hide_on("raw", self).combine_tools(tollbars).get(self)
        self.raw_x.add_tools(raw_hover_x)
        self.raw_x_axis = FigureMaker().x_axis_of(
            self.raw_x, self).combine_tools(tollbars).get(self)
        self.raw_x_axis.xaxis.axis_label = "Cov."
        self.raw_x_axis.xaxis.ticker = AdaptiveTicker(desired_num_ticks=3)
        self.raw_x.xgrid.ticker = AdaptiveTicker(desired_num_ticks=3, num_minor_ticks=1)
        self.raw_x.xgrid.grid_line_alpha = 0
        self.raw_x.xgrid.minor_grid_line_alpha = 0.5
        self.raw_x.ygrid.minor_grid_line_alpha = 0.5

        self.raw_y = FigureMaker().h(DEFAULT_SIZE).link_x(
            self.heatmap).hide_on("raw", self).combine_tools(tollbars).get(self)
        self.raw_y.add_tools(raw_hover_y)
        self.raw_y_axis = FigureMaker().y_axis_of(
            self.raw_y, self).combine_tools(tollbars).get(self)
        self.raw_y_axis.yaxis.axis_label = "Cov."
        self.raw_y_axis.yaxis.ticker = AdaptiveTicker(desired_num_ticks=3)
        self.raw_y.ygrid.ticker = AdaptiveTicker(desired_num_ticks=3, num_minor_ticks=1)
        self.raw_y.ygrid.grid_line_alpha = 0
        self.raw_y.ygrid.minor_grid_line_alpha = 0.5
        self.raw_y.xgrid.minor_grid_line_alpha = 0.5

        self.raw_x.multi_line(xs="values", ys="screen_pos", source=self.raw_data_x,
                        line_color="colors")  # , level="image"
        self.raw_y.multi_line(xs="screen_pos", ys="values", source=self.raw_data_y,
                        line_color="colors")  # , level="image"

        self.anno_x = FigureMaker().w(DEFAULT_SIZE).link_y(self.heatmap).hide_on(
            "annotation", self).combine_tools(tollbars).categorical_x().get(self)
        self.anno_x_axis = FigureMaker().x_axis_of(
            self.anno_x, self).combine_tools(tollbars).get(self)
        self.anno_x_axis.xaxis.axis_label = "Anno."
        self.anno_x.xgrid.minor_grid_line_alpha = 0
        self.anno_x.xgrid.grid_line_alpha = 0
        self.anno_x.ygrid.minor_grid_line_alpha = 0.5

        self.anno_y = FigureMaker().h(DEFAULT_SIZE).link_x(self.heatmap).hide_on(
            "annotation", self).combine_tools(tollbars).categorical_y().get(self)
        self.anno_y_axis = FigureMaker().y_axis_of(
            self.anno_y, self).combine_tools(tollbars).get(self)
        self.anno_y_axis.yaxis.axis_label = "Anno."
        self.anno_y.ygrid.minor_grid_line_alpha = 0
        self.anno_y.ygrid.grid_line_alpha = 0
        self.anno_y.xgrid.minor_grid_line_alpha = 0.5

        self.anno_x.vbar(x="anno_name", top="screen_end", bottom="screen_start", width=0.9, fill_color="color", line_color=None,
                         source=self.anno_x_data)
        self.anno_y.hbar(y="anno_name", right="screen_end", left="screen_start", height=0.9, fill_color="color", line_color=None,
                         source=self.anno_y_data)

        anno_hover = HoverTool(
            tooltips=[
                ('bin pos', "@chr @index_start - @index_end"),
                ('num_annotations', "@num_anno"),
                ('info', "@info"),
            ]
        )
        self.anno_x.add_tools(anno_hover)
        self.anno_y.add_tools(anno_hover)

        crosshair = CrosshairTool(dimensions="width", line_color="lightgrey")
        for fig in [self.anno_x, self.raw_x, self.heatmap]:
            fig.add_tools(crosshair)
        crosshair = CrosshairTool(dimensions="height", line_color="lightgrey")
        for fig in [self.anno_y, self.raw_y, self.heatmap]:
            fig.add_tools(crosshair)


        tool_bar = FigureMaker.get_tools(tollbars)
        #SETTINGS_WIDTH = tool_bar.width
        show_hide = self.make_show_hide_dropdown(
            ["settings", "interface", "show_hide"],
                ("Axes", "axis"), (RAW_PLOT_NAME, "raw"),
                                                   (ANNOTATION_PLOT_NAME, "annotation"), ("Tools", "tools"))

        in_group = self.dropdown_select("In Group", "tooltip_in_group",
                                             ("Sum [a+b+c+...]", "sum"), 
                                             ("Minimium [min(a,b,c,...)]", "min"),
                                             ("Maximum [max(a,b,c,...)]", "max"),
                                             ("Difference [|a-b|+|a-c|+|b-c|+...]", "dif"),
                                             ("Mean [mean(a,b,c,...)]", "mean"),
                                             active_item=['settings', 'replicates', 'in_group'])

        betw_group = self.dropdown_select("Between Group", "tooltip_between_groups",
                                               ("Sum [a+b]", "sum"), ("Show First Group [a]", "1st"), 
                                               ("Show Second Group [b]", "2nd"), ("Substract [a-b]", "sub"),
                                               ("Difference [|a-b|]", "dif"), ("Divide [a/b]", "div"),
                                               ("Minimum [min(a,b)]", "min"),  ("Maximum [max(a,b)]", "max"),
                                                active_item=['settings', 'replicates', 'between_group'])

        symmetrie = self.dropdown_select("Symmetry", "tooltip_symmetry",
                                              ("Show All Interactions", "all"), 
                                              ("Only Show Symmetric Interactions", "sym"),
                                              ("Only Show Asymmetric Interactions", "asym"),
                                              ("Make Interactions Symmetric (Bottom to Top)", "topToBot"), 
                                              ("Make Interactions Symmetric (Top to Bottom)", "botToTop"),
                                              active_item=['settings', 'filters', 'symmetry'])

        normalization = self.dropdown_select("Normalize by", "tooltip_normalize_by",
                                                  ("Reads per Million",
                                                   "rpm"), 
                                                  ("Reads per Thousand",
                                                   "rpk"), 
                                                  ("Binominal Test", "radicl-seq"),
                                                  ("Iterative Correction", "hi-c"),
                                                  ("No Normalization", "dont"),
                                                  active_item=['settings', 'normalization', 'normalize_by']
                                                  )

        color_scale = self.dropdown_select("Scale Color Range", "tooltip_scale_color_range",
                                                  ("by absolute max", "abs"), 
                                                  ("zero to max-value", "max"), 
                                                  ("min- to max-value", "minmax"), 
                                                  ("do not scale", "dont"),
                                                  active_item=['settings', 'normalization', 'scale']
                                                  )

        incomp_align_layout = self.make_checkbox("Show reads with incomplete alignments", 
                                                    settings=['settings', 'filters', 'incomplete_alignments'])

        divide_column = self.make_checkbox("Divide heatmap columns by track", 
                                                    settings=['settings', 'normalization', 'divide_by_column_coverage'])
        divide_row = self.make_checkbox("Divide heatmap rows by track", 
                                                    settings=['settings', 'normalization', 'divide_by_row_coverage'])


        ddd = self.make_checkbox("Divide by Distance Dependent Decay", "tooltip_ddd",
                                        settings=['settings', 'normalization', 'ddd'])

        square_bins = self.make_checkbox("Make Bins Squares", "tooltip_bin_aspect_ratio",
                                                   settings=['settings', "interface", "squared_bins"]
                                                   )

        power_ten_bin = self.make_checkbox("Snap Bin Size", "tooltip_snap_bin_size",
                                                settings=['settings', "interface", "snap_bin_size"]
                                            )

        color_picker = self.dropdown_select("Color Palette", "tooltip_color",
                                                ("Viridis", "Viridis256"),
                                                ("Plasma", "Plasma256"),
                                                ("Turbo", "Turbo256"),
                                                ("Low to High", "LowToHigh"),
                                                active_item=['settings', "interface", "color_palette"]
                                                  )

        multi_mapping = self.dropdown_select("Ambiguous Mapping", "tooltip_multi_mapping",
                                                ("Count read if all mapping loci are within a bin", "enclosed"),
                                                ("Count read if mapping loci bounding-box overlaps bin", "overlaps"),
                                                ("Count read if first mapping loci is within a bin", "first"),
                                                ("Count read if last mapping loci is within a bin", "last"),
                                                ("Count read if there is only one mapping loci", "points_only"),
                                                active_item=['settings', "filters", "ambiguous_mapping"]
                                                  )

        def axis_labels_event(e):
            self.session.set_value(["seetings", "interface", "axis_lables"], e)
            self.heatmap_y_axis.yaxis.axis_label = e.split("_")[0]
            self.heatmap_x_axis.xaxis.axis_label = e.split("_")[1]
        axis_lables = self.dropdown_select("Axis Labels", "tooltip_y_axis_label",
                                                  ("RNA / DNA", "RNA_DNA"),
                                                  ("DNA / RNA", "DNA_RNA"),
                                                  ("DNA / DNA", "DNA_DNA"), 
                                                  active_item=['settings', "interface", "axis_lables"],
                                                  event=axis_labels_event
                                                  )

        def stretch_event(val):
            self.session.set_value(["settings", "interface", "stretch"], val)
            if val:
                self.heatmap.sizing_mode = "stretch_both"
            else:
                self.heatmap.sizing_mode = "scale_height"
        stretch = self.make_checkbox("Stretch heatmap", "tooltip_stretch_scale",
                                            settings=["settings", "interface", "stretch"],
                                            on_change=stretch_event)

        ms_l = self.make_range_slider_spinner(width=SETTINGS_WIDTH, 
                                                settings=["settings", "filters", "mapping_q"], 
                                                title="Mapping Quality Bounds", sizing_mode="stretch_width")

        ibs_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                                                title="Minimum Interactions", 
                                                settings=["settings", "normalization", "min_interactions"], 
                                                sizing_mode="stretch_width")

        crs_l = self.make_range_slider_spinner(width=SETTINGS_WIDTH, 
                                                title="Color Scale Range", 
                                                settings=["settings", "normalization", "color_range"],
                                                sizing_mode="stretch_width")

        is_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                                          title="Color Scale Log Base", 
                                          settings=["settings", "normalization", "log_base"],
                                          sizing_mode="stretch_width")

        def update_freq_event(val):
            self.session.set_value(["settings", "interface", "update_freq", "val"], val)
        ufs_l = self.make_slider_spinner(width=SETTINGS_WIDTH,
                                            settings=["settings", "interface", "update_freq"],
                                            title="Update Frequency [seconds]", #, format="0[.]000"
                                            on_change=update_freq_event, sizing_mode="stretch_width")

        rs_l = self.make_slider_spinner(width=SETTINGS_WIDTH,
                                    settings=["settings", "interface", "zoom_redraw"],
                                    title="Redraw if zoomed in by [%]", sizing_mode="stretch_width")

        aas_l = self.make_slider_spinner(width=SETTINGS_WIDTH, settings=["settings", "interface", "add_draw_area"],
                                         title="Additional Draw Area [%]", sizing_mode="stretch_width")

        dds_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                                    settings=["settings", "filters", "min_diag_dist"],
                                       title="Minimum Distance from Diagonal (kbp)", sizing_mode="stretch_width")

        def anno_size_slider_event(val):
            self.session.set_value(["settings", "interface", "anno_size", "val"], val)
            self.anno_x.width = val
            self.anno_x_axis.width = val
            self.anno_y.height = val
            self.anno_y_axis.height = val
        ass_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                                      settings=["settings", "interface", "anno_size"],
                                       title=ANNOTATION_PLOT_NAME + " Plot Size", sizing_mode="stretch_width",
                                       on_change=anno_size_slider_event)

        def raw_size_slider_event(val):
            self.session.set_value(["settings", "interface", "raw_size", "val"], val)
            self.raw_x.width = val
            self.raw_x_axis.width = val
            self.raw_y.height = val
            self.raw_y_axis.height = val
        rss2_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                                      settings=["settings", "interface", "raw_size"],
                                      title=RAW_PLOT_NAME + " Plot Size", sizing_mode="stretch_width",
                                      on_change=raw_size_slider_event)

        nb_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                               settings=["settings", "interface", "max_num_bins"],
                               title="Max number of Bins (in thousands)", sizing_mode="stretch_width")

        rsa_l = self.make_slider_spinner(width=SETTINGS_WIDTH, 
                               settings=["settings", "normalization", "p_accept"],
                               title="pAccept for binominal test", sizing_mode="stretch_width")
            
        meta_file_label = Div(text="Data path:")
        meta_file_label.margin = DIV_MARGIN
        self.meta_file = TextInput(value="smoother_out/")
        self.meta_file.on_change("value", lambda x, y, z: self.setup())

        group_layout = self.multi_choice_auto("Replicates", 
                                                [[["replicates", "in_group_a"], "group A"], 
                                                [["replicates", "in_group_b"], "group B"], 
                                                [["replicates", "in_row"], "track row"], 
                                                [["replicates", "in_column"], "track col"],
                                                [["replicates", "cov_column_a"], "column A"], 
                                                [["replicates", "cov_column_b"], "column B"], 
                                                [["replicates", "cov_row_a"], "row A"], 
                                                [["replicates", "cov_row_b"], "row B"]],
                                                ["replicates", "list"])

        annos_layout = self.multi_choice_auto("Annotations", 
                                                         [[["annotation", "visible_y"], "displayed row"],
                                                          [["annotation", "visible_x"], "displayed col"], 
                                                          [["annotation", "row_filter"], "row filter"], 
                                                          [["annotation", "col_filter"], "column filter"]],
                                                        ["annotation", "list"])

        power_tick = FuncTickFormatter(
            code="""
            if (tick / 9 >= 7)
                return Math.ceil((1 + tick % 9)) + "*10^" + Math.floor(tick / 9) + "bp";
            else if (tick / 9 >= 3)
                return Math.ceil((1 + tick % 9) * Math.pow(10, Math.floor(tick / 9)-3)) + "kbp";
            else
                return Math.ceil((1 + tick % 9) * Math.pow(10, Math.floor(tick / 9))) + "bp"; """)
        self.min_max_bin_size = Slider( 
                start = 0,
                end = 1,
                value=0,
                title="Minimum Bin Size",
                format=power_tick, 
                sizing_mode="stretch_width")
        def min_bin_size_event():
            self.session.set_value(["settings", "interface", "min_bin_size", "val"], self.min_max_bin_size.value)
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

        norm_layout = self.multi_choice_auto("Normalization", 
                                                       [[["coverage", "in_column"], "track column"], 
                                                        [["coverage", "in_row"], "track row"], 
                                                        [["coverage", "cov_column_a"], "column A"], 
                                                        [["coverage", "cov_column_b"], "column B"], 
                                                        [["coverage", "cov_row_a"], "row A"], 
                                                        [["coverage", "cov_row_b"], "row B"]],
                                                        ["coverage", "list"])

        x_coords = self.dropdown_select_session("Column Coordinates", "tooltip_row_coordinates",
                                                ["contigs", "list"], ["contigs", "column_coordinates"], 
                                                [("Genomic loci", "full_genome")])

        y_coords = self.dropdown_select_session("Row Coordinates", "tooltip_column_coordinates",
                                                ["contigs", "list"], ["contigs", "row_coordinates"], 
                                                [("Genomic loci", "full_genome")])

        chrom_layout = self.multi_choice_auto("Chromosomes",
                                                        [[["contigs", "displayed_on_x"], "Rows"], 
                                                         [["contigs", "displayed_on_y"], "Columns"]],
                                                        ["contigs", "list"])

        multiple_anno_per_bin = self.dropdown_select("Multiple Annotations in Bin", 
                "tooltip_multiple_annotations_in_bin", 
                ("Combine region from first to last annotation", "combine"), 
                ("Use first annotation", "first"), 
                ("Use Random annotation", "random"), 
                ("Increase number of bins to match number of annotations (might be slow)", "force_separate"),
                active_item=["settings", "filters", "multiple_annos_in_bin"])

        self.export_button = self.dropdown_select("Export", "tooltip_export",
                                                  ("Current View", "current"),
                                                  ("Full Matrix", "full"),
                                                  active_item=["settings", "export", "area"])

        export_label = Div(text="Output Prefix:")
        export_label.margin = DIV_MARGIN
        self.export_file = TextInput()
        def export_file_event(_1, _2, _3):
            self.session.set_value(["settings", "export", "prefix"], self.export_file.value)
            self.trigger_render()
        self.export_file.on_change("value", export_file_event)
        
        export_sele_layout = self.multi_choice_auto("Export Selection", [[["settings", "export", "selection"], ""]],
                                                    ["settings", "export", "list"], orderable=False)
    
        self.low_color = ColorPicker(title="Color Low")
        self.high_color = ColorPicker(title="Color High")
        def color_event_low(_1, _2, _3):
            self.session.set_value(["settings", "interface", "color_low"], self.low_color.color)
            self.trigger_render()
        def color_event_high(_1, _2, _3):
            self.session.set_value(["settings", "interface", "color_high"], self.high_color.color)
            self.trigger_render()
        self.low_color.on_change("color", color_event_low)
        self.high_color.on_change("color", color_event_high)

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

        version_info = Div(text="Smoother "+ self.smoother_version +"<br>LibSps Version: " + Quarry.get_libSps_version())

        self.color_layout = row([self.make_color_figure(["black"])])


        quick_configs = [self.config_row("default", lock_name=True)]
        for idx in range(1,7):
            quick_configs.append(self.config_row(idx))

        SYM_WIDTH = 10
        SYM_CSS = ["other_button"]
        reset_session = Button(label="", css_classes=SYM_CSS + ["fa_reset"], width=SYM_WIDTH, 
                                  height=SYM_WIDTH, sizing_mode="fixed", button_type="light", align="center")
        def reset_event():
            with open(self.meta_file.value + ".smoother_index/default_session.json", 'r') as f:
                default_session = json.load(f)
                default_session["settings"] = self.session.get_value(["settings"])
            self.session.set_session(default_session)
            self.do_config()
            self.trigger_render()

        reset_session.on_click(reset_event)

        self.ticker_x = ExtraTicksTicker(extra_ticks=[])
        self.ticker_y = ExtraTicksTicker(extra_ticks=[])

        def get_formatter():
            return FuncTickFormatter(
                    args={"contig_starts": [], "genome_end": 0, "dividend": 1, "contig_names": []},
                    code="""
                            function numberWithCommas(x) {
                                return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                            }
                            if(tick < 0 || tick >= genome_end)
                                return "n/a";
                            var idx = 0;
                            while(contig_starts[idx + 1] <= tick)
                                idx += 1;
                            var tick_pos = dividend * (tick - contig_starts[idx]);
                            var tick_label = "";
                            if(tick_pos % 1000000 == 0)
                                tick_label = numberWithCommas(tick_pos / 1000000) + "mbp";
                            else if (tick_pos % 1000 == 0)
                                tick_label = numberWithCommas(tick_pos / 1000) + "kbp";
                            else
                                tick_label = numberWithCommas(tick_pos) + "bp";
                            return contig_names[idx] + ": " + tick_label;
                        """)
        
        self.tick_formatter_x = get_formatter()
        self.tick_formatter_y = get_formatter()

        self.heatmap_x_axis.xaxis[0].formatter = self.tick_formatter_x
        self.heatmap_y_axis.yaxis[0].formatter = self.tick_formatter_y


        self.undo_button = Button(label="", css_classes=SYM_CSS + ["fa_page_previous_solid"], width=SYM_WIDTH, 
                                  height=SYM_WIDTH, sizing_mode="fixed", button_type="light", align="center")
        def undo_event():
            self.session.undo()
            self.do_config()
            self.trigger_render()
        self.undo_button.on_click(undo_event)
        self.redo_button = Button(label="", css_classes=SYM_CSS + ["fa_page_next_solid"], width=SYM_WIDTH, 
                                  height=SYM_WIDTH, sizing_mode="fixed", button_type="light", align="center")
        def redo_event():
            self.session.redo()
            self.do_config()
            self.trigger_render()
        self.redo_button.on_click(redo_event)
        
        for plot in [self.heatmap, self.raw_y, self.anno_y, self.heatmap_x_axis]:
            plot.xgrid.ticker = self.ticker_x
            plot.xaxis.major_label_text_align = "left"
            plot.xaxis.ticker.min_interval = 1
        for plot in [self.heatmap, self.raw_x, self.anno_x, self.heatmap_y_axis]:
            plot.ygrid.ticker = self.ticker_y
            plot.yaxis.major_label_text_align = "right"
            plot.yaxis.ticker.min_interval = 1

        _settings = column([
                make_panel("General", "tooltip_general", [row([self.undo_button, self.redo_button, tool_bar, 
                                                                reset_session]), 
                                                          meta_file_label, self.meta_file]),
                make_panel("Normalization", "tooltip_normalization", [normalization, divide_column, divide_row,
                                    self.color_layout, ibs_l, crs_l, is_l, color_scale, norm_layout, rsa_l, ddd]),
                make_panel("Replicates", "tooltip_replicates", [in_group, betw_group, group_layout]),
                make_panel("Interface", "tooltip_interface", [nb_l,
                                    show_hide, mmbs_l,
                                    ufs_l, rs_l, aas_l, ass_l, rss2_l,
                                    stretch, square_bins, power_ten_bin, color_picker, 
                                    self.low_color, self.high_color, axis_lables]),
                make_panel("Filters", "tooltip_filters", [ms_l, incomp_align_layout, 
                                          symmetrie, dds_l, annos_layout, 
                                          x_coords, y_coords, multiple_anno_per_bin, chrom_layout, multi_mapping]),
                make_panel("Export", "tooltip_export", [export_label, self.export_file, export_sele_layout,
                                        #export_type_layout, 
                                      self.export_button]),
                make_panel("Presetting", "tooltip_quick_config", quick_configs),
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
        

        self.hidable_plots.append((_settings_n_info, ["tools"]))
        self.settings_row = row([Spacer(sizing_mode="stretch_both"), _settings_n_info, self.reshow_settings()], css_classes=["full_height"])
        self.settings_row.height = 100
        self.settings_row.min_height = 100
        self.settings_row.height_policy = "fixed"
        self.settings_row.width = SETTINGS_WIDTH
        self.settings_row.width_policy = "fixed"

        quit_ti = TextInput(value="keepalive", name="quit_ti", visible=False)
        quit_ti.on_change("value", lambda x, y, z: sys.exit())


        grid_layout = [
            [self.heatmap_y_axis, self.anno_x,   self.raw_x,
                      None,              self.heatmap,   self.settings_row],
            [None,              self.anno_x_axis, self.raw_x_axis,
                      None,              None,               None],
            [None,              None,             None,           
                self.raw_y_axis,   self.raw_y,         None],
            [None,              None,             None,       
                self.anno_y_axis,  self.anno_y,        None],
            [quit_ti,       None,             None,           
                None,            self.heatmap_x_axis, None],
        ]

        root_min_one = grid(grid_layout, sizing_mode="stretch_both")
        root_min_one.align = "center"
        self.root = grid([[root_min_one]])
        self.update_visibility()

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
        if "Include Annotation" in self.session.get_value(["settings", "export", "selection"]):
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
    def render(self, zoom_in_render):
        def unlocked_task():
            def cancelable_task():
                    
                def callback():
                    self.spinner.css_classes = ["fade-in"]
                self.curdoc.add_next_tick_callback(callback)


                self.render_step_log("setup_col_data_sources")
                self.session.update_cds()

                d_heatmap = self.session.get_heatmap()

                raw_data_x = self.session.get_tracks(True)
                raw_data_y = self.session.get_tracks(False)
                min_max_tracks_x = self.session.get_min_max_tracks(True)
                min_max_tracks_y = self.session.get_min_max_tracks(False)

                d_anno_x = self.session.get_annotation(False)
                d_anno_y = self.session.get_annotation(True)
                displayed_annos_x = self.session.get_displayed_annos(False)
                if len(displayed_annos_x) == 0:
                    displayed_annos_x.append("")
                displayed_annos_y = self.session.get_displayed_annos(True)
                if len(displayed_annos_y) == 0:
                    displayed_annos_y.append("")

                b_col = self.session.get_background_color()

                render_area = self.session.get_drawing_area()

                canvas_size_x, canvas_size_y = self.session.get_canvas_size()
                tick_list_x = self.session.get_tick_list(True)
                tick_list_y = self.session.get_tick_list(False)
                ticks_x = self.session.get_ticks(True)
                ticks_y = self.session.get_ticks(False)

                palette = self.session.get_palette()

                w_bin, h_bin = self.session.get_bin_size()
                #print(colors)

                self.render_step_log("transfer_data")

                @gen.coroutine
                def callback():
                    self.curdoc.hold()
                    #if self.settings['replicates']['between_group'] == "sub":
                    #    palette = [xxx/50 - 1 for xxx in range(100)]
                    #else:
                    #    palette = [xxx/100 for xxx in range(100)]
                    self.color_layout.children = [self.make_color_figure(palette)]
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
                    #if self.do_export is None:
                    #    if len(self.displayed_annos) == 0:
                    #        self.anno_x.x_range.factors = [""]
                    #        self.anno_y.y_range.factors = [""]
                    #    else:
                    #        self.anno_x.x_range.factors = self.displayed_annos
                    #        self.anno_y.y_range.factors = self.displayed_annos

                    def readable_display(l):
                        def add_commas(x):
                            return "{:,}".format(x)
                        if l % 1000000 == 0:
                            return str(add_commas(l // 1000000)) + "mbp"
                        elif l % 1000 == 0:
                            return str(add_commas(l // 1000)) + "kbp"
                        else:
                            return str(add_commas(l)) + "bp"

                    end_text = "Rendering Done.<br>Current Bin Size: " + readable_display(w_bin) + \
                                " x " + readable_display(h_bin) + "."


                    if self.do_export is None:
                        self.raw_x_axis.xaxis.bounds = (min_max_tracks_x[0], min_max_tracks_x[1])
                        self.raw_y_axis.yaxis.bounds = (min_max_tracks_y[0], min_max_tracks_y[1])

                        def set_bounds(plot, left=None, right=None, top=None, bottom=None, color=None):
                            ra = self.plot_render_area(plot)
                            ra.left = render_area[0] if left is None else left
                            ra.bottom = render_area[1] if bottom is None else bottom
                            ra.right = render_area[2] if right is None else right
                            ra.top = render_area[3] if top is None else top
                            if not color is None:
                                ra.fill_color = color

                        set_bounds(self.raw_x, left=min_max_tracks_x[0], right=min_max_tracks_x[1])
                        set_bounds(self.raw_y, bottom=min_max_tracks_y[0], top=min_max_tracks_y[1])
                        set_bounds(self.anno_x, left=0, right=len(displayed_annos_x))
                        set_bounds(self.anno_y, bottom=0, top=len(displayed_annos_y))

                        set_bounds(self.heatmap, color=b_col)

                        self.heatmap_data.data = d_heatmap
                        self.raw_data_x.data = raw_data_x
                        self.raw_data_y.data = raw_data_y
                        #self.ratio_data_x.data = ratio_data_x
                        #self.ratio_data_y.data = ratio_data_y
                        
                        #self.anno_x.x_range.factors = []
                        #self.anno_y.y_range.factors = []
                        self.anno_x.x_range.factors = displayed_annos_x
                        self.anno_y.y_range.factors = displayed_annos_y[::-1]

                        #self.anno_x_data.data = {}
                        #self.anno_y_data.data = {}
                        self.anno_x_data.data = d_anno_x
                        self.anno_y_data.data = d_anno_y
                        #self.overlay_data.data = d_overlay

                        self.heatmap.x_range.reset_start = 0
                        self.heatmap.x_range.reset_end = canvas_size_x
                        self.heatmap.y_range.reset_start = 0
                        self.heatmap.y_range.reset_end = canvas_size_y

                        self.ticker_x.extra_ticks = tick_list_x
                        self.ticker_y.extra_ticks = tick_list_y

                        self.tick_formatter_x.args = ticks_x
                        self.tick_formatter_y.args = ticks_y

                        
                        for plot in [self.heatmap, self.raw_y, self.anno_y, self.heatmap_x_axis]:
                            plot.xgrid.bounds = (0, canvas_size_x)
                            plot.xaxis.bounds = (0, canvas_size_x)
                        for plot in [self.heatmap, self.raw_x, self.anno_x, self.heatmap_y_axis]:
                            plot.ygrid.bounds = (0, canvas_size_y)
                            plot.yaxis.bounds = (0, canvas_size_y)

                    self.do_export = None
                    self.curdoc.unhold()
                    total_time, ram_usage = self.render_done(0)#len(bins[0]) if len(bins) > 0 else 0)
                    self.curr_bin_size.text = end_text + "<br>Took " + str(total_time) + " in total.<br>" + str(ram_usage) + "% RAM used.<br> " #+ str(len(bins[0])//1000) if len(bins) > 0 else "0" + "k bins rendered."
                    self.curdoc.add_timeout_callback(
                        lambda: self.render_callback(),
                            self.session.get_value(["settings", "interface", "update_freq", "val"])*1000)

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

                self.curdoc.add_next_tick_callback(callback)
                return True
            while cancelable_task() is None:
                pass
            def callback():
                self.spinner.css_classes = ["fade-out"]
                self.session.save_session()
            self.curdoc.add_next_tick_callback(callback)

        self.undo_button.disabled = not self.session.has_undo()
        self.undo_button.css_classes = ["other_button", "fa_page_previous" if self.undo_button.disabled else "fa_page_previous_solid"]
        self.redo_button.disabled = not self.session.has_redo()
        self.redo_button.css_classes = ["other_button", "fa_page_next" if self.redo_button.disabled else "fa_page_next_solid"]
        yield executor.submit(unlocked_task)

    def setup(self):
        print("loading index...\033[K")
        self.spinner.css_classes = ["fade-in"]
        def callback():
            self.curr_bin_size.text = "loading index..."
            def callback2():
                if os.path.exists(self.meta_file.value + ".smoother_index"):
                    self.session = Quarry(self.meta_file.value + ".smoother_index")

                    if self.session.get_value(["settings"]) is None:
                        with open('smoother/static/conf/default.json', 'r') as f:
                            settings = json.load(f)
                        #print(settings)
                        self.session.set_value(["settings"], settings)


                    print("done loading\033[K")
                    self.do_config()
                    self.trigger_render()
                    self.curr_bin_size.text = "done loading"
                    self.render_callback() # @todo this is not good here!!!!
                else:
                    print("File not found")
                    self.curr_bin_size.text = "File not found. <br>Waiting for Fileinput."
            self.curdoc.add_next_tick_callback(callback2)
        self.curdoc.add_next_tick_callback(callback)

    def trigger_render(self):
        self.session.cancel()
        self.force_render = True

    def render_callback(self):
        if self.do_render:
            if not None in (self.heatmap.x_range.start, self.heatmap.x_range.end, self.heatmap.y_range.start,
                            self.heatmap.y_range.end):

                curr_area = (self.heatmap.x_range.start, self.heatmap.y_range.start,
                             self.heatmap.x_range.end, self.heatmap.y_range.end)
                curr_area_size = (curr_area[2] - curr_area[0]) * (curr_area[3] - curr_area[1])
                min_change = 1-self.session.get_value(["settings", "interface", "zoom_redraw", "val"])/100
                zoom_in_render = False
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

                    area_dict = {
                        "x_start": curr_area[0],
                        "x_end": curr_area[2],
                        "y_start": curr_area[1],
                        "y_end": curr_area[3],
                    }
                    self.session.set_value(["area"], area_dict)

                    self.session.cancel()

                    def callback():
                        self.last_drawing_area = self.session.get_drawing_area()
                        self.render(zoom_in_render)
                    self.curdoc.add_next_tick_callback(callback)
                    return

            self.curdoc.add_timeout_callback(
                lambda: self.render_callback(), self.session.get_value(["settings", "interface", "update_freq", "val"])*1000)

    def set_root(self):
        self.curdoc.clear()
        self.curdoc.add_root(self.root)
        self.curdoc.title = "Smoother"
        self.do_render = True
        self.force_render = True


