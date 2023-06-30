__author__ = "Markus Schmidt"
__email__ = "Markus.Schmidt@lmu.de"

from bokeh.layouts import grid, row, column
from bokeh.plotting import figure, curdoc
from bokeh.models import (
    ColumnDataSource,
    Dropdown,
    Button,
    RangeSlider,
    Slider,
    TextInput,
    FuncTickFormatter,
    Div,
    HoverTool,
    Spinner,
    CheckboxGroup,
    CrosshairTool,
    ColorPicker,
    DataTable,
    TableColumn,
    CellEditor,
    Panel, 
    Tabs, 
    Spacer, 
    Slope, 
    CustomJS
)
from bokeh.transform import jitter
import math
from datetime import datetime
from tornado import gen
from bokeh.document import without_document_lock
import os
import sys
from bokeh.palettes import Viridis256, Colorblind, Plasma256, Turbo256
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from bokeh.models.tickers import AdaptiveTicker
from libbiosmoother import Quarry, export_tsv, export_png, export_svg, open_default_json
import json
from bin.figure_maker import FigureMaker, DROPDOWN_HEIGHT, FONT
from bin.extra_ticks_ticker import *
import bin.global_variables
import numpy as np
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources
from pathlib import Path

SETTINGS_WIDTH = 400
BUTTON_HEIGHT = 30
DEFAULT_SIZE = 50
ANNOTATION_PLOT_NAME = "Annotation panel"
RAW_PLOT_NAME = "Secondary data panel"

DIV_MARGIN = (5, 5, 0, 5)
BTN_MARGIN = (3, 3, 3, 3)
BTN_MARGIN_2 = (3, 3, 3, 3)

CONFIG_FILE_VERSION = 0.1

DEFAULT_TEXT_INPUT_HEIGHT = 30

executor = ThreadPoolExecutor(max_workers=1)

biosmoother_home_folder = str(Path.home()) + "/.biosmoother"


class MainLayout:
    def dropdown_select_h(self, title, event, tooltip):
        ret = Dropdown(
            label=title,
            menu=[],
            width=SETTINGS_WIDTH,
            sizing_mode="fixed",
            css_classes=["other_button", "tooltip", tooltip],
            height=DROPDOWN_HEIGHT,
        )

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
                d[key] = key == str(active_item)
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
            self.dropdown_select_config.append(
                (lambda x: set_menu([*options], x), active_item)
            )
        else:
            set_menu(options)
        return ret

    def dropdown_select_session(
        self, title, tooltip, session_key, active_item, add_keys=[], event=None
    ):
        if event is None:

            def default_event(e):
                self.session.set_value(active_item, e)
                self.trigger_render()

            event = default_event
        ret, set_menu = self.dropdown_select_h(title, event, tooltip)

        def set_menu_2(x):
            set_menu(
                add_keys + [(x, x) for x in self.session.get_value(session_key)], x
            )

        self.dropdown_select_config.append((set_menu_2, active_item))
        return ret

    def update_multi_choice(self, obj):
        if obj in self.updatable_multi_choice:
            self.updatable_multi_choice[obj]()

    def multi_choice(
        self,
        label,
        tooltip,
        checkboxes,
        session_key=None,
        callback=None,
        orderable=True,
        renamable=False,
        title="",
    ):
        if callback is None:

            def default_callback(n, cb):
                for v in cb.values():
                    self.session.set_value(v[0], v[1])
                if not session_key is None:
                    self.session.set_value(session_key, n)
                self.trigger_render()

            callback = default_callback

        def make_source():
            source = {}
            source["idx"] = []
            if orderable:
                source["up"] = []
                source["down"] = []
            source["names"] = []
            for _, n in checkboxes:
                source[n] = []
            return source

        def make_columns():
            columns = []

            if orderable:
                columns.append(TableColumn(field="idx", title="#", editor=CellEditor()))
                columns.append(TableColumn(field="up", title="", editor=CellEditor()))
                columns.append(TableColumn(field="down", title="", editor=CellEditor()))
            else:
                columns.append(TableColumn(field="idx", title="#", editor=CellEditor()))

            if renamable:
                columns.append(
                    TableColumn(field="names", title=label, editor=CellEditor())
                )
            else:
                # @todo-low-prio eventually allow rename -> remove editor and fix callback below
                columns.append(
                    TableColumn(field="names", title=label, editor=CellEditor())
                )

            for k, n in checkboxes:
                columns.append(TableColumn(field=n, title=n, editor=CellEditor()))
            return columns

        select_ret = TextInput(value="")
        data_table = DataTable(
            source=ColumnDataSource(make_source()),
            columns=make_columns(),
            editable=True,
            autosize_mode="fit_columns",
            index_position=None,
            width=SETTINGS_WIDTH,
            tags=["blub"],
            height=150,
            sortable=False
        )

        source_code = """
            var grids = document.getElementsByClassName('grid-canvas');
            for (var k = 0,kmax = grids.length; k < kmax; k++){
                if(grids[k].outerHTML.includes('active')){
                    var grid = grids[k].children;
                    for (var i = 0,max = grid.length; i < max; i++){
                        if (grid[i].outerHTML.includes('active')){
                            for (var j = 0, jmax = grid[i].children.length; j < jmax; j++)
                                if(grid[i].children[j].outerHTML.includes('active')) { 
                                    select_ret.value = grid[i].children[0].textContent + " " + grid[i].children[j].className;
                                }
                        }
                    }
                }
            }
        """
        js_callback = CustomJS(args={"select_ret": select_ret}, code=source_code)

        self.reset_options[label] = [{}, []]

        filter_t_in = TextInput(placeholder="filter...")

        def set_options(labels, active_dict):
            self.reset_options[label] = [active_dict, labels]
            source = make_source()
            if len(labels) > 1:
                source["idx"].append("")
                if orderable:
                    source["up"].append("")
                    source["down"].append("")
                source["names"].append("select all")
                for _, n in checkboxes:
                    bools = [name in active_dict[n] for name in labels]
                    source[n].append("☑" if all(bools) else ("☐" if all(not b for b in bools) else "·"))
            for idx, name in enumerate(labels):
                if filter_t_in.value.lower() in name.lower() or len(filter_t_in.value) == 0:
                    source["idx"].append(str(idx))
                    if orderable:
                        source["up"].append("▲" if idx > 0 else "")
                        source["down"].append("▼" if idx < len(labels) - 1 else "")
                    source["names"].append(name)
                    for _, n in checkboxes:
                        source[n].append("☑" if name in active_dict[n] else "☐")

            data_table.source.data = source
            data_table.frozen_rows=1 if len(labels) > 1 else 0
            # data_table.columns = make_columns()

        filter_t_in.on_change("value", lambda _x, _y, _z: set_options(
                        self.reset_options[label][1], self.reset_options[label][0]
                    ))

        def trigger_callback():
            cb = {}
            order = self.reset_options[label][1]
            for k, n in checkboxes:
                cb[n] = (k, [])
                for opt in order:
                    if opt in self.reset_options[label][0][n]:
                        cb[n][1].append(opt)
            callback(order, cb)

        def move_element(opt, idx, up):
            if up and idx > 0:
                return opt[: idx - 1] + [opt[idx], opt[idx - 1]] + opt[idx + 1 :]
            elif not up and idx + 1 < len(opt):
                return opt[:idx] + [opt[idx + 1], opt[idx]] + opt[idx + 2 :]
            return opt

        def get_select():
            sp = select_ret.value.split()
            print(sp)
            if len(sp) > 0:
                if sp[0] != 'slick-cell':
                    y = int(sp[0])
                else:
                    y = None
                for s in sp[1:]:
                    if s[0] == "l":
                        x = int(s[1:]) - (4 if orderable else 2)
                return x, y
            return None, None

        def py_callback(attr, old, new):
            if new != []:
                x, y = get_select()
                if orderable and x == -3 and not y is None:
                    self.reset_options[label][1] = move_element(
                        self.reset_options[label][1], y, True
                    )
                    set_options(
                        self.reset_options[label][1], self.reset_options[label][0]
                    )
                    trigger_callback()
                elif orderable and x == -2 and not y is None:
                    self.reset_options[label][1] = move_element(
                        self.reset_options[label][1], y, False
                    )
                    set_options(
                        self.reset_options[label][1], self.reset_options[label][0]
                    )
                    trigger_callback()
                elif x >= 0:
                    if y is None:
                        n = checkboxes[x][1]
                        bools = [not name in self.reset_options[label][0][n] for name in self.reset_options[label][1]]
                        if all(bools):
                            # nothing is activate -> set everything active
                            self.reset_options[label][0][n] = self.reset_options[label][1]
                        else: # none(bools) or some(bools)
                            # some things are active -> set everything inactive
                            self.reset_options[label][0][n] = []
                    else:
                        local_label = self.reset_options[label][1][y]
                        n = checkboxes[x][1]
                        if local_label in self.reset_options[label][0][n]:
                            self.reset_options[label][0][n].remove(local_label)
                        else:
                            self.reset_options[label][0][n].append(local_label)
                    set_options(
                        self.reset_options[label][1], self.reset_options[label][0]
                    )
                    trigger_callback()
            data_table.source.selected.update(indices=[])

        data_table.source.selected.on_change("indices", py_callback)
        data_table.source.selected.js_on_change("indices", js_callback)

        def on_change_rename(attr, old, new):
            return
            x, y = get_select()
            print("change", x, y)
            if orderable and x == -4:
                r_opt = self.reset_options[label][1]
                self.reset_options[label][1] = r_opt
            # print(new)
            pass

        data_table.source.on_change("data", on_change_rename)

        layout = column(
            [row([Div(text=title), filter_t_in], sizing_mode="stretch_width"), data_table],
            sizing_mode="stretch_width",
            css_classes=["outlnie_border", "tooltip", tooltip],
        )

        def update():
            set_options(self.reset_options[label][1], self.reset_options[label][0])

        self.updatable_multi_choice[layout] = update

        return set_options, layout

    def multi_choice_auto(
        self,
        label,
        tooltip,
        checkboxes,
        session_key,
        callback=None,
        orderable=True,
        title="",
    ):
        set_options, layout = self.multi_choice(
            label, tooltip, checkboxes, session_key, callback, orderable, title=title
        )
        self.multi_choice_config.append((set_options, session_key, checkboxes))
        return layout

    def config_row(self, file_nr, callback=None, lock_name=False):
        SYM_WIDTH = 10
        SYM_CSS = ["other_button"]

        with open_default_json() if file_nr == "default" else (
            pkg_resources.files("biosmoother")
            / "static"
            / "conf"
            / (str(file_nr) + ".json")
        ).open("r") as f:
            factory_default = json.load(f)
        out_file = biosmoother_home_folder + "/conf/" + str(file_nr) + ".json"
        if not os.path.exists(out_file):
            with open(out_file, "w") as f:
                json.dump(factory_default, f)
        with open(out_file, "r") as f:
            settings = json.load(f)

        if CONFIG_FILE_VERSION != settings["smoother_config_file_version"]:
            print(
                "Config file version does not match: expected",
                CONFIG_FILE_VERSION,
                "but got",
                settings["smoother_config_file_version"],
            )

        name = TextInput(
            value=settings["display_name"],
            sizing_mode="stretch_width",
            disabled=lock_name or bin.global_variables.no_save,
            height=DEFAULT_TEXT_INPUT_HEIGHT,
        )
        apply_button = Button(
            label="",
            css_classes=SYM_CSS + ["fa_apply"],
            width=SYM_WIDTH,
            height=SYM_WIDTH,
            sizing_mode="fixed",
            button_type="light",
            align="center",
        )
        save_button = Button(
            label="",
            css_classes=SYM_CSS + ["fa_save"],
            width=SYM_WIDTH,
            height=SYM_WIDTH,
            sizing_mode="fixed",
            button_type="light",
            align="center",
        )
        reset_button = Button(
            label="",
            css_classes=SYM_CSS + ["fa_reset"]
            if settings != factory_default
            else ["fa_reset_disabled"],
            width=SYM_WIDTH,
            height=SYM_WIDTH,
            sizing_mode="fixed",
            button_type="light",
            align="center",
            disabled=settings == factory_default,
        )

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

            if not bin.global_variables.quiet:
                print("saving...")
            settings = dict_diff(
                self.session.get_value(["settings"]), self.settings_default
            )
            settings["display_name"] = name.value
            settings["smoother_config_file_version"] = CONFIG_FILE_VERSION
            with open(
                biosmoother_home_folder + "/conf/" + str(file_nr) + ".json", "w"
            ) as f:
                json.dump(settings, f)
            reset_button.disabled = settings == factory_default
            reset_button.css_classes = (
                SYM_CSS + ["fa_reset"]
                if settings != factory_default
                else ["fa_reset_disabled"]
            )
            if not bin.global_variables.quiet:
                print("saved")

        save_button.on_click(lambda _: save_event())

        def reset_event():
            with (
                pkg_resources.files("biosmoother")
                / "static"
                / "conf"
                / (str(file_nr) + ".json")
            ).open("r") as f_in:
                with open(
                    biosmoother_home_folder + "/conf/" + str(file_nr) + ".json", "w"
                ) as f_out:
                    for l in f_in:
                        f_out.write(l)
            reset_button.disabled = True
            reset_button.css_classes = SYM_CSS + ["fa_reset_disabled"]
            with open(
                biosmoother_home_folder + "/conf/" + str(file_nr) + ".json", "r"
            ) as f:
                settings = json.load(f)
            name.value = settings["display_name"]

        reset_button.on_click(lambda _: reset_event())

        def apply_event():
            if not bin.global_variables.quiet:
                print("applying...")
            with open(
                biosmoother_home_folder + "/conf/" + str(file_nr) + ".json", "r"
            ) as f:
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

            self.session.set_value(
                ["settings"],
                combine_dict(settings, self.session.get_value(["settings"])),
            )
            self.curdoc.hold()
            self.do_config()
            self.curdoc.unhold()
            self.trigger_render()
            if not bin.global_variables.quiet:
                print("applied")

        apply_button.on_click(lambda _: apply_event())

        if bin.global_variables.no_save:
            return row([name, apply_button, reset_button], sizing_mode="stretch_width")
        else:
            return row(
                [
                 name, 
                 apply_button, 
                 save_button, 
                 reset_button
                 ],
                sizing_mode="stretch_width",
            )

    def make_slider_spinner(
        self,
        title,
        tooltip,
        settings,
        width=200,
        on_change=None,
        spinner_width=80,
        sizing_mode="stretch_width",
    ):
        if on_change is None:

            def default_on_change(val):
                self.session.set_value(settings + ["val"], val)
                self.trigger_render()

            on_change = default_on_change
        spinner = Spinner(width=spinner_width)
        slider = Slider(
            title=title,
            show_value=False,
            width=width - spinner_width,
            sizing_mode=sizing_mode,
            start=0,
            end=1,
            value=0,
        )

        spinner.js_link("value", slider, "value")
        slider.js_link("value", spinner, "value")
        slider.on_change("value_throttled", lambda _x, _y, _z: on_change(slider.value))
        spinner.on_change(
            "value_throttled", lambda _x, _y, _z: on_change(spinner.value)
        )

        self.slider_spinner_config.append((slider, spinner, on_change, settings))

        return row(
            [slider, spinner],
            width=width,
            margin=DIV_MARGIN,
            css_classes=["tooltip", tooltip],
        )

    def make_range_slider_spinner(
        self,
        title,
        tooltip,
        settings,
        width=200,
        on_change=None,
        spinner_width=80,
        sizing_mode="stretch_width",
    ):
        if on_change is None:

            def default_on_change(val):
                self.session.set_value(settings + ["val_min"], val[0])
                self.session.set_value(settings + ["val_max"], val[1])
                self.trigger_render()

            on_change = default_on_change
        slider = RangeSlider(
            title=title,
            show_value=False,
            width=width - spinner_width * 2,
            sizing_mode=sizing_mode,
            start=0,
            end=1,
            value=(0, 1),
        )
        spinner_start = Spinner(width=spinner_width)
        spinner_end = Spinner(width=spinner_width)

        spinner_start.js_on_change(
            "value",
            CustomJS(
                args=dict(other=slider),
                code="other.value = [this.value, other.value[1]]",
            ),
        )
        slider.js_link("value", spinner_start, "value", attr_selector=0)

        spinner_end.js_on_change(
            "value",
            CustomJS(
                args=dict(other=slider),
                code="other.value = [other.value[0], this.value]",
            ),
        )
        slider.js_link("value", spinner_end, "value", attr_selector=1)

        slider.on_change("value_throttled", lambda _x, _y, _z: on_change(slider.value))
        spinner_end.on_change(
            "value_throttled", lambda _x, _y, _z: on_change(slider.value)
        )
        spinner_start.on_change(
            "value_throttled", lambda _x, _y, _z: on_change(slider.value)
        )

        self.range_slider_spinner_config.append(
            (slider, spinner_start, spinner_end, on_change, settings)
        )

        return row(
            [slider, spinner_start, spinner_end],
            width=width,
            margin=DIV_MARGIN,
            css_classes=["tooltip", tooltip],
        )

    def make_checkbox(
        self, title, tooltip="", settings=[], on_change=None, width=SETTINGS_WIDTH
    ):
        div = Div(text=title, sizing_mode="stretch_width", width=width - 20)
        cg = CheckboxGroup(labels=[""], width=20)
        if on_change is None:

            def default_event(active):
                self.session.set_value(settings, active)
                self.trigger_render()

            on_change = default_event
        cg.on_change("active", lambda _1, _2, _3: on_change(0 in cg.active))

        self.checkbox_config.append((cg, settings))

        return row(
            [div, cg], width=width, margin=DIV_MARGIN, css_classes=["tooltip", tooltip]
        )

    def config_slider_spinner(self):
        for slider, spinner, on_change, session_key in self.slider_spinner_config:
            value = self.session.get_value(session_key + ["val"])
            start = self.session.get_value(session_key + ["min"])
            end = self.session.get_value(session_key + ["max"])
            step = self.session.get_value(session_key + ["step"])

            spinner_min = self.session.get_value(
                session_key + ["spinner_min_restricted"]
            )
            spinner_max = self.session.get_value(
                session_key + ["spinner_max_restricted"]
            )

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
        for (
            slider,
            spinner_start,
            spinner_end,
            on_change,
            session_key,
        ) in self.range_slider_spinner_config:
            value_min = self.session.get_value(session_key + ["val_min"])
            value_max = self.session.get_value(session_key + ["val_max"])
            start = self.session.get_value(session_key + ["min"])
            end = self.session.get_value(session_key + ["max"])
            step = self.session.get_value(session_key + ["step"])

            spinner_min = self.session.get_value(
                session_key + ["spinner_min_restricted"]
            )
            spinner_max = self.session.get_value(
                session_key + ["spinner_max_restricted"]
            )

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
                d[name] = [
                    ele for ele in ele_list if ele in self.session.get_value(key)
                ]
            set_options(ele_list, d)

    def set_v4c_range(self):
        self.v4c_col_expected = self.get_readable_range(
            self.session.get_value(["settings", "interface", "v4c", "col_from"]),
            self.session.get_value(["settings", "interface", "v4c", "col_to"]),
            False,
            genomic_coords=True,
        )
        self.v4c_col.value = self.v4c_col_expected

        self.v4c_row_expected = self.get_readable_range(
            self.session.get_value(["settings", "interface", "v4c", "row_from"]),
            self.session.get_value(["settings", "interface", "v4c", "row_to"]),
            True,
            genomic_coords=True,
        )
        self.v4c_row.value = self.v4c_row_expected
        self.trigger_render()

    def parse_v4c(self):
        change = False
        if self.v4c_col.value != self.v4c_col_expected:
            col_start, col_end = self.interpret_range(self.v4c_col.value, False, genomic_coords=True)
            change = True
            if not col_start is None:
                self.session.set_value(
                    ["settings", "interface", "v4c", "col_from"], col_start
                )
            if not col_end is None:
                self.session.set_value(
                    ["settings", "interface", "v4c", "col_to"], col_end
                )

        if self.v4c_row.value != self.v4c_row_expected:
            row_start, row_end = self.interpret_range(self.v4c_row.value, True, genomic_coords=True)
            change = True
            if not row_start is None:
                self.session.set_value(
                    ["settings", "interface", "v4c", "row_from"], row_start
                )
            if not row_end is None:
                self.session.set_value(
                    ["settings", "interface", "v4c", "row_to"], row_end
                )

        if change:
            self.set_v4c_range()

    def do_config(self):
        def to_idx(x):
            if x <= 0:
                return 0
            power = int(math.log10(x))
            return 9 * power + math.ceil(x / 10**power) - 1

        min_ = max(
            to_idx(self.session.get_value(["dividend"])),
            self.session.get_value(["settings", "interface", "min_bin_size", "min"]),
        )
        val_ = max(
            to_idx(self.session.get_value(["dividend"])),
            self.session.get_value(["settings", "interface", "min_bin_size", "val"]),
        )

        self.session.set_value(["settings", "interface", "min_bin_size", "min"], min_)
        self.session.set_value(["settings", "interface", "min_bin_size", "val"], val_)

        self.min_max_bin_size.start = self.session.get_value(
            ["settings", "interface", "min_bin_size", "min"]
        )
        self.min_max_bin_size.end = self.session.get_value(
            ["settings", "interface", "min_bin_size", "max"]
        )
        self.min_max_bin_size.value = self.session.get_value(
            ["settings", "interface", "min_bin_size", "val"]
        )
        self.min_max_bin_size.step = self.session.get_value(
            ["settings", "interface", "min_bin_size", "step"]
        )

        self.undo_button.disabled = not self.session.has_undo()
        self.undo_button.css_classes = [
            "other_button",
            "fa_page_previous"
            if self.undo_button.disabled
            else "fa_page_previous_solid",
        ]
        self.redo_button.disabled = not self.session.has_redo()
        self.redo_button.css_classes = [
            "other_button",
            "fa_page_next" if self.redo_button.disabled else "fa_page_next_solid",
        ]

        self.heatmap.x_range.start = self.session.get_value(["area", "x_start"])
        self.heatmap.x_range.end = self.session.get_value(["area", "x_end"])
        self.heatmap.y_range.start = self.session.get_value(["area", "y_start"])
        self.heatmap.y_range.end = self.session.get_value(["area", "y_end"])

        self.config_slider_spinner()
        self.config_range_slider_spinner()
        self.config_dropdown()
        self.config_checkbox()
        self.config_multi_choice()

        self.low_color.color = self.session.get_value(
            ["settings", "interface", "color_low"]
        )
        self.high_color.color = self.session.get_value(
            ["settings", "interface", "color_high"]
        )

        self.config_show_hide(
            self.session.get_value(["settings", "interface", "show_hide"])
        )

        self.export_file.value = self.session.get_value(
            ["settings", "export", "prefix"]
        )

        self.set_v4c_range()

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
        
        x_visible = len(self.raw_data_x.data["values"]) > 0
        self.raw_x.visible = self.show_hide["raw"] and x_visible
        self.raw_x_axis.visible = self.show_hide["raw"] and x_visible
        y_visible = len(self.raw_data_y.data["values"]) > 0
        self.raw_y.visible = self.show_hide["raw"] and y_visible
        self.raw_y_axis.visible = self.show_hide["raw"] and y_visible
        self.anno_x.visible = len(self.anno_y_data.data["anno_name"]) > 0 and self.show_hide["annotation"]
        self.anno_x_axis.visible =self.anno_x.visible
        self.anno_y.visible = len(self.anno_y_data.data["anno_name"]) > 0 and self.show_hide["annotation"]
        self.anno_y_axis.visible =self.anno_y.visible

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
                (("☑ " if self.show_hide[key] or key == "tools" else "☐ ") + name, key)
            )
        menu.append(
            (
                ("☑ " if self.show_hide["grid_lines"] else "☐ ") + "Grid Lines",
                "grid_lines",
            )
        )
        menu.append(
            (
                ("☑ " if self.show_hide["indent_line"] else "☐ ") + "Identity Line",
                "indent_line",
            )
        )
        menu.append(
            (
                ("☑ " if self.show_hide["contig_borders"] else "☐ ") + "Contig Borders",
                "contig_borders",
            )
        )
        return menu

    def make_show_hide_dropdown(self, session_key, *names):
        for _, key in names:
            if key == "tools":
                self.show_hide[key] = True
            elif key not in self.show_hide:
                self.show_hide[key] = False
        self.names = names

        self.show_hide_dropdown = Dropdown(
            label="Show/Hide",
            menu=self.make_show_hide_menu(),
            width=SETTINGS_WIDTH,
            sizing_mode="fixed",
            css_classes=["other_button", "tooltip", "tooltip_show_hide"],
            height=DROPDOWN_HEIGHT,
        )

        def event(e):
            self.toggle_hide(e.item)
            self.session.set_value(
                session_key + [e.item],
                not self.session.get_value(session_key + [e.item]),
            )
            self.show_hide_dropdown.menu = self.make_show_hide_menu()

        self.show_hide_dropdown.on_click(event)

        self.show_hide_dropdown.js_on_click(CustomJS(code="setTimeout(function(){window.dispatchEvent(new Event('resize'));}, 100)"))
        return self.show_hide_dropdown

    def config_show_hide(self, settings):
        for key in self.show_hide.keys():
            self.show_hide[key] = settings[key]
        self.show_hide_dropdown.menu = self.make_show_hide_menu()
        self.update_visibility()

    def reshow_settings(self):
        self.unhide_button = Button(
            label="<", width=40, height=40, css_classes=["other_button"]
        )
        self.unhide_button.sizing_mode = "fixed"
        self.unhide_button.visible = False

        def event(e):
            if self.session is not None:
                self.session.set_value(
                    ["settings", "interface", "show_hide", "tools"], True
                )
            self.toggle_hide("tools")

        self.unhide_button.on_click(event)
        return self.unhide_button

    def make_color_figure(self, palette):
        def hex_to_rgb(value):
            value = value.lstrip('#')
            lv = len(value)
            return [int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3)]
        color_figure = figure(tools="", height=125, width=SETTINGS_WIDTH)
        color_figure.x(0, 0, color=None)
        scatter = color_figure.scatter(x="ranged_score", y=jitter("0", 1, distribution="normal"), 
                             line_color=None, color="color",
                             source=self.heatmap_data)
        img = np.empty((1, len(palette)), dtype=np.uint32)
        view = img.view(dtype=np.uint8).reshape((1, len(palette), 4))
        for i, p in enumerate(palette):
            r, g, b = hex_to_rgb(p)
            view[0, i, 0] = r
            view[0, i, 1] = g
            view[0, i, 2] = b
            view[0, i, 3] = 255
        color_figure.image_rgba(image=[img], x=0, y=-5.5, dw=1, dh=1)
        color_figure.add_tools(
            HoverTool(
                tooltips=[
                    (
                        "(x, y)",
                        "(@chr_x @index_left .. @index_right, @chr_y @index_bottom .. @index_top)",
                    ),
                    ("score", "@score_total"),
                    ("reads by group", "A: @score_a, B: @score_b"),
                ]
            )
        )
        color_figure.hover.renderers = [scatter]

        # make plot invisible
        color_figure.axis.visible = False
        color_figure.toolbar_location = None
        color_figure.border_fill_alpha = 0
        color_figure.outline_line_alpha = 0
        color_figure.xgrid.grid_line_color = None
        color_figure.ygrid.grid_line_color = None

        return color_figure

    def to_readable_pos(self, x, genome_end, contig_names, contig_starts, lcs=0):
        if len(contig_names) == 0 or len(contig_starts) == 0:
            return "n/a"
        x = int(x)
        oob = x > genome_end * self.session.get_value(["dividend"]) or x < 0
        if x < 0:
            idx = 0
        elif x >= genome_end * self.session.get_value(["dividend"]):
            idx = len(contig_names) - 1
            x -= contig_starts[-1] * self.session.get_value(["dividend"])
        else:
            idx = 0
            for idx, (start, end) in enumerate(
                zip(contig_starts, contig_starts[1:] + [genome_end])
            ):
                if x >= start * self.session.get_value(
                    ["dividend"]
                ) and x < end * self.session.get_value(["dividend"]):
                    x -= start * self.session.get_value(["dividend"])
                    break

        if x == 0:
            label = "0 bp"
        elif x % 1000000 == 0:
            label = "{:,}".format(x // 1000000) + " mbp"
        elif x % 1000 == 0:
            label = "{:,}".format(x // 1000) + " kbp"
        else:
            label = "{:,}".format(x) + " bp"

        if idx >= len(contig_names):
            return "n/a"

        if lcs != 0:
            n = contig_names[idx][:-lcs]
        else:
            n = contig_names[idx]
        return n + ": " + label

    def get_readable_range(self, start, end, x_y, genomic_coords=False):
        lcs = self.session.get_longest_common_suffix(self.print)
        contig_names = self.session.get_annotation_list(x_y, self.print)
        if genomic_coords:
            contig_starts = self.session.get_contig_start_list(x_y, self.print)
        else:
            contig_starts = self.session.get_tick_list(x_y, self.print)
        if len(contig_starts) > 0:
            return (
                self.to_readable_pos(
                    start * int(self.session.get_value(["dividend"])),
                    contig_starts[-1],
                    contig_names,
                    contig_starts[:-1],
                    lcs,
                )
                + " .. "
                + self.to_readable_pos(
                    end * int(self.session.get_value(["dividend"])),
                    contig_starts[-1],
                    contig_names,
                    contig_starts[:-1],
                    lcs,
                )
            )
        else:
            return "n/a"

    def set_area_range(self):
        self.area_range_expected = (
            "X=["
            + self.get_readable_range(
                int(math.floor(self.heatmap.x_range.start)),
                int(math.ceil(self.heatmap.x_range.end)),
                True,
            )
            + "] Y=["
            + self.get_readable_range(
                int(math.floor(self.heatmap.y_range.start)),
                int(math.ceil(self.heatmap.y_range.end)),
                False,
            )
            + "]"
        )
        self.area_range.value = self.area_range_expected

    def isint(self, num):
        try:
            int(num)
            return True
        except ValueError:
            return False

    def interpret_number(self, s):
        if s[-1:] == "b":
            s = s[:-1]
        elif s[-2:] == "bp":
            s = s[:-2]
        fac = 1
        if len(s) > 0 and s[-1] == "m":
            fac = 1000000
            s = s[:-1]
        if len(s) > 0 and s[-1] == "k":
            fac = 1000
            s = s[:-1]
        s = s.replace(",", "")
        if self.isint(s):
            return (int(s) * fac) // self.session.get_value(["dividend"])
        return None

    def interpret_position(self, s, x_y, bot=True, genomic_coords=False):
        if s.count(":") == 0 and s.count("+-") == 1:
            x, y = s.split("+-")
            c = self.interpret_number(y)
            if not c is None and bot:
                c = -c
            a = self.session.interpret_name(x, x_y, bot, genomic_coords)
            if not a is None and not c is None:
                return [a + c]
        elif s.count(":") == 1:
            x, y = s.split(":")
            if "+-" in y:
                y1, y2 = y.split("+-")
                if len(y1) == 0:
                    b = 0
                else:
                    b = self.interpret_number(y1)
                c = self.interpret_number(y2)
                if not c is None and bot:
                    c = -c
                a = self.session.interpret_name(x, x_y, bot if len(y1) == 0 else True, genomic_coords)
                if not a is None and not b is None and not c is None:
                    return [a + b + c]
            b = self.interpret_number(y)
            a = self.session.interpret_name(x, x_y, True, genomic_coords)
            if not a is None and not b is None:
                return [a + b]

        a = self.interpret_number(s)
        if not a is None:
            return [a]

        if not s is None:
            a = self.session.interpret_name(s, x_y, bot, genomic_coords)
            if not a is None:
                return [a]

        return [None]

    def interpret_range(self, s, x_y, genomic_coords=False):
        s = "".join(s.lower().split())
        if s.count("..") == 1 and s.count("[") <= 1 and s.count("]") <= 1:
            x, y = s.split("..")
            if x[:1] == "[":
                x = x[1:]
            if y[-1:] == "]":
                y = y[:-1]

            return self.interpret_position(x, x_y, True, genomic_coords=genomic_coords) + self.interpret_position(
                y, x_y, False, genomic_coords=genomic_coords
            )
        if s[:1] == "[":
            s = s[1:]
        if s[-1:] == "]":
            s = s[:-1]
        return self.interpret_position(s, x_y, True, genomic_coords=genomic_coords) + self.interpret_position(
            s, x_y, False, genomic_coords=genomic_coords
        )

    def interpret_area(self, s):
        # remove all space-like characters
        s = "".join(s.lower().split())
        if s.count(";") == 1 and s.count("x=") == 0 and s.count("y=") == 0:
            x, y = s.split(";")
            return self.interpret_range(x, True) + self.interpret_range(y, False)

        if s.count("x=") == 1 and s[:2] == "x=" and s.count("y=") == 0:
            s = s[2:]
            return self.interpret_range(s, True) + [
                self.heatmap.y_range.start,
                self.heatmap.y_range.end,
            ]

        if s.count("x=") == 0 and s.count("y=") == 1 and s[:2] == "y=":
            s = s[2:]
            return [
                self.heatmap.x_range.start,
                self.heatmap.x_range.end,
            ] + self.interpret_range(s, True)

        if s.count("x=") == 1 and s.count("y=") == 1:
            x_pos = s.find("x=")
            y_pos = s.find("y=")
            x = s[x_pos + 2 : y_pos] if x_pos < y_pos else s[x_pos + 2 :]
            y = s[y_pos + 2 : x_pos] if y_pos < x_pos else s[y_pos + 2 :]
            return self.interpret_range(x, True) + self.interpret_range(y, False)

        return self.interpret_range(s, True) + self.interpret_range(s, False)

    def parse_area_range(self):
        if self.area_range_expected != self.area_range.value:
            i = self.interpret_area(self.area_range.value)
            if not i[0] is None and not i[1] is None:
                self.heatmap.x_range.start = min(i[0], i[1])
                self.heatmap.x_range.end = max(i[0], i[1], min(i[0], i[1]) + 1)
            elif not i[0] is None:
                self.heatmap.x_range.start = i[0]
            elif not i[1] is None:
                self.heatmap.x_range.end = i[1]
            if not i[2] is None and not i[3] is None:
                self.heatmap.y_range.start = min(i[2], i[3])
                self.heatmap.y_range.end = max(i[2], i[3], min(i[2], i[3]) + 1)
            elif not i[2] is None:
                self.heatmap.y_range.start = i[2]
            elif not i[3] is None:
                self.heatmap.y_range.end = i[3]

    def save_tools(self, tools):
        if not self.session is None:
            self.session.set_value(["settings", "active_tools"], tools.split(";"))

    def make_tabs(self, tabs, sizing_mode="stretch_both", outer=False):
        t = Tabs(tabs=tabs, sizing_mode=sizing_mode)
        return t

    def make_panel(self, title, tooltip="", children=[], inner=True):
        return Panel(title=title, child=column(children, visible=True))

    @gen.coroutine
    @without_document_lock
    def do_export(self):
        def unlocked_task():
            def callback():
                self.spinner.css_classes = ["fade-in"]

            self.curdoc.add_next_tick_callback(callback)

            if self.session.get_value(["settings", "export", "export_format"]) == "tsv":
                export_tsv(self.session)
            elif (
                self.session.get_value(["settings", "export", "export_format"]) == "svg"
            ):
                export_svg(self.session)
            elif (
                self.session.get_value(["settings", "export", "export_format"]) == "png"
            ):
                export_png(self.session)
            else:
                self.print("invalid value for export_format")

            def callback():
                self.spinner.css_classes = ["fade-out"]
                self.print_status(
                    "done exporting. Current Bin Size: " + self.get_readable_bin_size()
                )

            self.curdoc.add_next_tick_callback(callback)

        yield executor.submit(unlocked_task)

    def __init__(self):
        self.show_hide = {
            "grid_lines": False,
            "contig_borders": True,
            "indent_line": False,
        }
        self.hidable_plots = []
        self.grid_line_plots = []
        self.unhide_button = None
        self.render_areas = {}
        self.slope = None
        self.show_hide_dropdown = None
        self.names = None

        self.x_coords_d = "full_genome"

        self.force_render = True
        self.curdoc = curdoc()
        self.last_drawing_area = (0, 0, 0, 0)
        self.curr_area_size = 1
        self.biosmoother_version = "?"
        self.reset_options = {}
        self.session = Quarry(bin.global_variables.biosmoother_index)
        # self.session.verbosity = 5
        if not os.path.exists(biosmoother_home_folder + "/conf/"):
            os.makedirs(biosmoother_home_folder + "/conf/")
        if not os.path.exists(biosmoother_home_folder + "/conf/default.json"):
            with open_default_json() as f_in:
                with open(biosmoother_home_folder + "/conf/default.json", "w") as f_out:
                    for l in f_in:
                        f_out.write(l)

        with open(biosmoother_home_folder + "/conf/default.json", "r") as f:
            self.settings_default = json.load(f)

        self.heatmap = None
        d = {
            "screen_bottom": [],
            "screen_left": [],
            "screen_top": [],
            "screen_right": [],
            "color": [],
            "chr_x": [],
            "chr_y": [],
            "index_left": [],
            "index_right": [],
            "index_bottom": [],
            "index_top": [],
            "score_total": [],
            "score_a": [],
            "score_b": [],
            "0": [],
            "ranged_score": [],
        }
        self.heatmap_data = ColumnDataSource(data=d)
        d = {"b": [], "l": [], "t": [], "r": []}
        self.overlay_data = ColumnDataSource(data=d)
        self.overlay_dataset_id = None
        self.heatmap_x_axis = None
        self.heatmap_x_axis_2 = None
        self.heatmap_y_axis = None
        self.heatmap_y_axis_2 = None
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
        d = {
            "anno_name": [],
            "screen_start": [],
            "screen_end": [],
            "color": [],
            "chr": [],
            "index_start": [],
            "index_end": [],
            "info": [],
            "num_anno": [],
            "size": [],
            "strand": [],
            "id": [],
            "desc": [],
        }
        self.anno_x_data = ColumnDataSource(data=d)
        self.anno_y_data = ColumnDataSource(data=d)
        self.min_max_bin_size = None
        self.info_status_bar = None
        self.spinner = None
        self.info_field = None
        self.settings_row = None
        self.slider_spinner_config = []
        self.range_slider_spinner_config = []
        self.dropdown_select_config = []
        self.checkbox_config = []
        self.multi_choice_config = []
        self.export_file = None
        self.ticker_x = None
        self.ticker_x_2 = None
        self.ticker_y = None
        self.ticker_y_2 = None
        self.tick_formatter_x = None
        self.tick_formatter_x_2 = None
        self.tick_formatter_y = None
        self.tick_formatter_y_2 = None
        self.undo_button = None
        self.redo_button = None
        self.color_layout = None
        self.area_range = None
        self.area_range_expected = "n/a"
        self.updatable_multi_choice = {}
        d = {
            "chrs": [],
            "index_start": [],
            "index_end": [],
            "xs": [],
            "ys": [],
            "colors": [],
            "anno_desc": [],
            "sample_id": [],
            "anno_idx": [],
        }
        self.ranked_columns_data = ColumnDataSource(data=d)
        self.ranked_columns = None
        self.ranked_rows_data = ColumnDataSource(data=d)
        self.ranked_rows = None
        d = {"chr": [], "color": [], "xs": [], "ys": []}
        self.dist_dep_dec_plot_data = ColumnDataSource(data=d)
        self.dist_dep_dec_plot = None
        self.log_div = None
        self.log_div_text = ""
        self.v4c_col_expected = ""
        self.v4c_col = None
        self.v4c_row_expected = ""
        self.v4c_row = None

        self.do_layout()

    def do_layout(self):
        self.curdoc.clear()
        global SETTINGS_WIDTH
        tollbars = []
        self.heatmap = FigureMaker().name("heatmap").range1d().scale().combine_tools(tollbars).get(self)
        self.heatmap.min_border_left = 3
        self.heatmap.min_border_right = 3
        self.heatmap.min_border_bottom = 3
        self.heatmap.min_border_top = 3

        self.heatmap.quad(
            left="screen_left",
            bottom="screen_bottom",
            right="screen_right",
            top="screen_top",
            fill_color="color",
            line_color=None,
            source=self.heatmap_data,
            level="underlay",
        )
        self.heatmap.xgrid.minor_grid_line_alpha = 0.5
        self.heatmap.ygrid.minor_grid_line_alpha = 0.5

        self.heatmap.quad(
            left="l",
            bottom="b",
            right="r",
            top="t",
            fill_color=None,
            line_color="red",
            source=self.overlay_data,
            level="underlay",
        )

        self.overlay_dataset_id = Spinner(
            title="Overlay Lines Dataset Id",
            low=-1,
            step=1,
            value=-1,
            width=DEFAULT_SIZE,
            mode="int",
        )
        self.overlay_dataset_id.on_change(
            "value_throttled", lambda x, y, z: self.trigger_render()
        )

        self.heatmap.add_tools(
            HoverTool(
                tooltips=[
                    (
                        "(x, y)",
                        "(@chr_x @index_left .. @index_right, @chr_y @index_bottom .. @index_top)",
                    ),
                    ("score", "@score_total"),
                    ("reads by group", "A: @score_a, B: @score_b"),
                ]
            )
        )

        self.heatmap_x_axis = (
            FigureMaker()
            .x_axis_of(self.heatmap, self, "", True, hide_keyword="coords")
            .combine_tools(tollbars)
            .name("heatmap_x_axis")
            .get(self)
        )
        self.heatmap_x_axis_2 = (
            FigureMaker()
            .x_axis_of(self.heatmap, self, "", True, hide_keyword="regs")
            .combine_tools(tollbars)
            .name("heatmap_x_axis_2")
            .get(self)
        )
        self.heatmap_x_axis_3 = (
            FigureMaker()
            .x_axis_of(self.heatmap, self, "", True, hide_keyword="regs")
            .combine_tools(tollbars)
            .name("heatmap_x_axis_3")
            .get(self)
        )

        # self.heatmap_x_axis.xaxis.minor_tick_line_color = None
        self.heatmap_y_axis = (
            FigureMaker()
            .y_axis_of(self.heatmap, self, "", True, hide_keyword="coords")
            .combine_tools(tollbars)
            .name("heatmap_y_axis")
            .get(self)
        )
        self.heatmap_y_axis_2 = (
            FigureMaker()
            .y_axis_of(self.heatmap, self, "", True, hide_keyword="regs")
            .combine_tools(tollbars)
            .name("heatmap_y_axis_2")
            .get(self)
        )
        self.heatmap_y_axis_3 = (
            FigureMaker()
            .y_axis_of(self.heatmap, self, "", True, hide_keyword="regs")
            .combine_tools(tollbars)
            .name("heatmap_y_axis_3")
            .get(self)
        )

        # self.heatmap_y_axis.yaxis.minor_tick_line_color = None

        self.slope = Slope(gradient=1, y_intercept=0, line_color=None)
        self.heatmap.add_layout(self.slope)

        raw_hover_x = HoverTool(
            tooltips="""
                <div>
                    <span style="color: @colors">@names: $data_x</span>
                </div>
            """,
            mode="hline",
        )
        raw_hover_y = HoverTool(
            tooltips="""
                <div>
                    <span style="color: @colors">@names: $data_y</span>
                </div>
            """,
            mode="vline",
        )

        self.raw_x = (
            FigureMaker()
            .w(DEFAULT_SIZE)
            .link_y(self.heatmap)
            .hidden()
            .hide_on("raw", self)
            .combine_tools(tollbars)
            .name("raw_x")
            .get(self)
        )
        self.raw_x.add_tools(raw_hover_x)
        self.raw_x_axis = (
            FigureMaker().x_axis_of(self.raw_x, self).combine_tools(tollbars).name("raw_x_axis").get(self)
        )
        self.raw_x_axis.xaxis.ticker = AdaptiveTicker(
            desired_num_ticks=3, num_minor_ticks=0
        )
        self.raw_x.xgrid.ticker = AdaptiveTicker(desired_num_ticks=3, num_minor_ticks=1)
        self.raw_x.xgrid.grid_line_alpha = 0
        self.raw_x.xgrid.minor_grid_line_alpha = 0.5
        self.raw_x.ygrid.minor_grid_line_alpha = 0.5

        self.raw_y = (
            FigureMaker()
            .h(DEFAULT_SIZE)
            .link_x(self.heatmap)
            .hidden()
            .hide_on("raw", self)
            .combine_tools(tollbars)
            .name("raw_y")
            .get(self)
        )
        self.raw_y.add_tools(raw_hover_y)
        self.raw_y_axis = (
            FigureMaker().y_axis_of(self.raw_y, self).combine_tools(tollbars).name("raw_y_axis").get(self)
        )
        self.raw_y_axis.yaxis.ticker = AdaptiveTicker(
            desired_num_ticks=3, num_minor_ticks=0
        )
        self.raw_y.ygrid.ticker = AdaptiveTicker(desired_num_ticks=3, num_minor_ticks=1)
        self.raw_y.ygrid.grid_line_alpha = 0
        self.raw_y.ygrid.minor_grid_line_alpha = 0.5
        self.raw_y.xgrid.minor_grid_line_alpha = 0.5

        self.raw_x.multi_line(
            xs="values", ys="screen_pos", source=self.raw_data_x, line_color="colors"
        )  # , level="image"
        self.raw_y.multi_line(
            xs="screen_pos", ys="values", source=self.raw_data_y, line_color="colors"
        )  # , level="image"

        self.anno_x = (
            FigureMaker()
            .w(DEFAULT_SIZE)
            .link_y(self.heatmap)
            .hidden()
            .hide_on("annotation", self)
            .combine_tools(tollbars)
            .categorical_x()
            .name("anno_x")
            .get(self)
        )
        self.anno_x_axis = (
            FigureMaker().x_axis_of(self.anno_x, self).combine_tools(tollbars).name("anno_x_axis").get(self)
        )
        self.anno_x.xgrid.minor_grid_line_alpha = 0
        self.anno_x.xgrid.grid_line_alpha = 0
        self.anno_x.ygrid.minor_grid_line_alpha = 0.5

        self.anno_y = (
            FigureMaker()
            .h(DEFAULT_SIZE)
            .link_x(self.heatmap)
            .hidden()
            .hide_on("annotation", self)
            .combine_tools(tollbars)
            .categorical_y()
            .name("anno_y")
            .get(self)
        )
        self.anno_y_axis = (
            FigureMaker().y_axis_of(self.anno_y, self).combine_tools(tollbars).name("anno_y_axis").get(self)
        )
        self.anno_y.ygrid.minor_grid_line_alpha = 0
        self.anno_y.ygrid.grid_line_alpha = 0
        self.anno_y.xgrid.minor_grid_line_alpha = 0.5

        self.anno_x.vbar(
            x="anno_name",
            top="screen_end",
            bottom="screen_start",
            width="size",
            fill_color="color",
            line_color=None,
            source=self.anno_x_data,
        )
        self.anno_y.hbar(
            y="anno_name",
            right="screen_end",
            left="screen_start",
            height="size",
            fill_color="color",
            line_color=None,
            source=self.anno_y_data,
        )

        anno_hover = HoverTool(
            tooltips=[
                ("bin pos", "@chr @index_start - @index_end"),
                ("num_annotations", "@num_anno"),
                ("ID", "@id"),
                ("strand", "@strand"),
                ("description", "@desc"),
                ("add. info", "@info"),
            ]
        )
        self.anno_x.add_tools(anno_hover)
        self.anno_y.add_tools(anno_hover)

        ranked_hover = HoverTool(
            tooltips=[
                ("pos", "@chrs @index_start - @index_end"),
                ("ranking", "@xs"),
                ("coverage", "@ys"),
                ("desc", "@anno_desc"),
                ("anno. index", "@anno_idx"),
                ("sample index", "@sample_id"),
            ]
        )
        self.ranked_columns = figure(
            tools="pan,wheel_zoom,box_zoom,crosshair",
            y_axis_type="log",
            height=200,
            width=SETTINGS_WIDTH,
        )
        tollbars.append(self.ranked_columns.toolbar)
        self.ranked_columns.dot(
            x="xs", y="ys", color="colors", size=12, source=self.ranked_columns_data
        )
        self.ranked_columns.xaxis.axis_label = "Samples ranked by RNA reads per kbp"
        self.ranked_columns.yaxis.axis_label = "RNA reads per kbp"
        self.ranked_columns.add_tools(ranked_hover)

        self.ranked_rows = figure(
            tools="pan,wheel_zoom,box_zoom,crosshair",
            y_axis_type="log",
            height=200,
            width=SETTINGS_WIDTH,
        )
        self.ranked_rows.toolbar_location = None
        self.ranked_rows.dot(
            x="xs", y="ys", color="colors", size=12, source=self.ranked_rows_data
        )
        self.ranked_rows.xaxis.axis_label = "Samples ranked by max. DNA reads in bin"
        self.ranked_rows.yaxis.axis_label = "Maximal DNA reads in bin"
        self.ranked_rows.add_tools(ranked_hover)

        self.dist_dep_dec_plot = figure(
            title="Distance Dependant Decay",
            tools="pan,wheel_zoom,box_zoom,crosshair",
            y_axis_type="log",
            height=200,
            width=SETTINGS_WIDTH,
        )
        self.dist_dep_dec_plot.xaxis.axis_label = "manhatten distance from diagonal"
        self.dist_dep_dec_plot.yaxis.axis_label = "reads per kbp^2"
        self.dist_dep_dec_plot.multi_line(
            xs="xs", ys="ys", color="color", source=self.dist_dep_dec_plot_data
        )

        for p in [self.ranked_columns, self.ranked_rows, self.dist_dep_dec_plot]:
            p.sizing_mode = "stretch_width"
            p.toolbar_location = None
            tollbars.append(p.toolbar)
            p.xaxis.axis_label_text_font_size = "11px"
            p.yaxis.axis_label_text_font_size = "11px"
            p.xaxis.axis_label_standoff = 0
            p.yaxis.axis_label_standoff = 0
            p.xaxis.major_label_text_font = FONT
            p.yaxis.major_label_text_font = FONT
            p.xaxis.axis_label_text_font = FONT
            p.yaxis.axis_label_text_font = FONT
            p.dot(x=[1], y=[1], fill_alpha=0, line_alpha=0)

        self.dist_dep_dec_plot.xaxis[0].formatter = FuncTickFormatter(
            args={},
            code="""
                    function numberWithCommas(x) {
                        return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                    }
                    var tick_label = "";
                    if(tick == 0)
                        tick_label = "0 bp"
                    else if(tick % 1000000 == 0)
                        tick_label = numberWithCommas(tick / 1000000) + " mbp";
                    else if (tick % 1000 == 0)
                        tick_label = numberWithCommas(tick / 1000) + " kbp";
                    else
                        tick_label = numberWithCommas(tick) + " bp";
                    return tick_label;
                """,
        )
        self.dist_dep_dec_plot.add_tools(
            HoverTool(
                tooltips="""
                <div>
                    <span style="color: @color">@chr: ($data_x, $data_y)</span>
                </div>
            """
            )
        )

        crosshair = CrosshairTool(dimensions="width", line_color="lightgrey")
        for fig in [self.anno_x, self.raw_x, self.heatmap]:
            fig.add_tools(crosshair)
        crosshair = CrosshairTool(dimensions="height", line_color="lightgrey")
        for fig in [self.anno_y, self.raw_y, self.heatmap]:
            fig.add_tools(crosshair)

        tool_bar = FigureMaker.get_tools(tollbars)
        show_hide = self.make_show_hide_dropdown(
            ["settings", "interface", "show_hide"],
            ("Secondary Axes", "axis"),
            ("Coordinates", "coords"),
            ("Regions", "regs"),
            (RAW_PLOT_NAME, "raw"),
            (ANNOTATION_PLOT_NAME, "annotation"),
            ("Options Panel", "tools"),
        )


        in_group = self.dropdown_select(
            "Merge datasets by",
            "tooltip_in_group",
            ("Sum [a+b+c+...]", "sum"),
            ("Minimium [min(a,b,c,...)]", "min"),
            ("Maximum [max(a,b,c,...)]", "max"),
            ("Difference [|a-b|+|a-c|+|b-c|+...]", "dif"),
            ("Mean [mean(a,b,c,...)]", "mean"),
            active_item=["settings", "replicates", "in_group"],
        )

        betw_group = self.dropdown_select(
            "Compare datapools by",
            "tooltip_between_groups",
            ("Sum [a+b]", "sum"),
            ("Show First Group [a]", "1st"),
            ("Show Second Group [b]", "2nd"),
            ("Substract [a-b]", "sub"),
            ("Difference [|a-b|]", "dif"),
            ("Divide [a/b]", "div"),
            ("Minimum [min(a,b)]", "min"),
            ("Maximum [max(a,b)]", "max"),
            active_item=["settings", "replicates", "between_group"],
        )

        symmetrie = self.dropdown_select(
            "Symmetry",
            "tooltip_symmetry",
            ("Show All Interactions", "all"),
            ("Only Show Symmetric Interactions", "sym"),
            ("Only Show Asymmetric Interactions", "asym"),
            ("Mirror Interactions to be Symmetric", "mirror"),
            active_item=["settings", "filters", "symmetry"],
        )

        last_bin_in_contig = self.dropdown_select(
            "Remainder Bin",
            "tooltip_remainder_bin",
            ("Merge remainder into last fullsized bin", "larger"),
            ("Hide remainder", "skip"),
            ("Display remainder", "smaller"),
            ("Make contig smaller", "fit_chrom_smaller"),
            ("Make contig larger", "fit_chrom_larger"),
            ("Extend remainder bin into next contig (only visual)", "cover_multiple"),
            active_item=["settings", "filters", "cut_off_bin"],
        )
        contig_smaller_than_bin = self.make_checkbox(
            "Fill contigs that are smaller than one bin",
            "tooltip_cibtug_snakker_than_bin", # @todo
            settings=["settings", "filters", "show_contig_smaller_than_bin"],
        )

        norm_sele = [
                ("Reads per million", "rpm"),
                ("Reads per thousand", "rpk"),
                ("Binominal test", "radicl-seq"),
                ("Iterative Correction", "ice"),
                ("Associated slices", "grid-seq"),
                ("No normalization", "dont"),
            ]
        if Quarry.has_cooler_icing():
            norm_sele.append((("Cooler Iterative Correction", "cool-ice")))

        normalization = self.dropdown_select(
            "Normalize heatmap by",
            "tooltip_normalize_by",
            *norm_sele,
            active_item=["settings", "normalization", "normalize_by"],
        )
        normalization_cov = self.dropdown_select(
            "Normalize coverage by",
            "tooltip_normalize_by_coverage",
            ("Reads per million", "rpm"),
            ("Reads per thousand", "rpk"),
            ("Reads per million base pairs", "rpmb"),
            ("Reads per thousand base pairs", "rpkb"),
            ("No normalization", "dont"),
            active_item=["settings", "normalization", "normalize_by_coverage"],
        )

        color_scale = self.dropdown_select(
            "Scale Color Range",
            "tooltip_scale_color_range",
            ("absolute max [x' = x / max(|v| in V)]", "abs"),
            ("max [x' = x / max(v in V)]", "max"),
            (
                "min-max [x' = (x + min(v in V)) / (max(v in V) - min(v in V))]",
                "minmax",
            ),
            ("do not scale [x' = x]", "dont"),
            active_item=["settings", "normalization", "scale"],
        )

        incomp_align_layout = self.make_checkbox(
            "Show multi-mapping reads with incomplete mapping loci lists",
            "tooltip_incomplete_alignments",
            settings=["settings", "filters", "incomplete_alignments"],
        )

        ddd = self.make_checkbox(
            "Normalize Primary data",
            "tooltip_ddd",
            settings=["settings", "normalization", "ddd"],
        )
        ddd_show = self.make_checkbox(
            "Display",
            "tooltip_ddd_show",
            settings=["settings", "normalization", "ddd_show"],
        )
        ddd_ex_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_ddd_quantiles",
            title="Percentile of samples to keep [%]",
            settings=["settings", "normalization", "ddd_quantile"],
            sizing_mode="stretch_width",
        )
        ice_sparse_filter = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_ice_sparse_filter",
            title="filter out slices with too many empty bins [%]",
            settings=["settings", "normalization", "ice_sparse_slice_filter"],
            sizing_mode="stretch_width",
        )
        ice_num_samples = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_ice_num_samples", # @todo
            title="Number of samples",
            settings=["settings", "normalization", "num_ice_bins"],
            sizing_mode="stretch_width",
        )
        ice_show_bias = self.make_checkbox(
            "Show Bias",
            "tooltip_ice_show_bias", # @todo
            settings=["settings", "normalization", "ice_show_bias"],
        )
        ice_local = self.make_checkbox(
            "Local Ice",
            "tooltip_local_ice", # @todo
            settings=["settings", "normalization", "ice_local"],
        )
        ddd_sam_l = self.make_range_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_ddd_samples",
            title="Number of samples",
            settings=["settings", "normalization", "ddd_samples"],
            sizing_mode="stretch_width",
        )

        square_bins = self.make_checkbox(
            "Make Bins Squares",
            "tooltip_bin_aspect_ratio",
            settings=["settings", "interface", "squared_bins"],
        )
        do_redraw = self.make_checkbox(
            "Auto Render",
            "tooltip_do_redraw", # @todo
            settings=["settings", "interface", "do_redraw"],
        )
        render_now = Button(
            label="Render Now",
            width=SETTINGS_WIDTH,
            sizing_mode="fixed",
            css_classes=["other_button", "tooltip", "tooltip_render_now"], # @todo
            height=DROPDOWN_HEIGHT,
        )

        def render_now_event(x):
            self.force_render = True
            self.trigger_render()

        render_now.on_click(render_now_event)

        power_ten_bin = self.make_checkbox(
            "Snap Bin Size",
            "tooltip_snap_bin_size",
            settings=["settings", "interface", "snap_bin_size"],
        )

        color_picker = self.dropdown_select(
            "Color Palette",
            "tooltip_color",
            ("Viridis", "Viridis256"),
            ("Plasma", "Plasma256"),
            ("Turbo", "Turbo256"),
            ("Fall", "Fall"),
            ("Low to High", "LowToHigh"),
            active_item=["settings", "interface", "color_palette"],
        )

        multi_mapping = self.dropdown_select(
            "Multi-Mapping reads (MMR)",
            "tooltip_multi_mapping",
            ("Count MMR if all mapping loci are within the same bin", "enclosed"),
            ("Count MMR if mapping loci minimum bounding-box overlaps bin", "overlaps"),
            ("Count MMR if bottom left mapping loci is within a bin", "first"),
            ("Count MMR if top right mapping loci is within a bin", "last"),
            ("Ignore MMRs", "points_only"),
            active_item=["settings", "filters", "ambiguous_mapping"],
        )
        directionality = self.dropdown_select(
            "Directionality",
            "tooltip_directionality",
            ("Count pairs where reads map to any strand", "all"),
            ("Count pairs where reads map to the same strand", "same"),
            ("Count pairs where reads map to opposite strands", "oppo"),
            ("Count pairs where reads map to the forward strand", "forw"),
            ("Count pairs where reads map to the reverse strand", "rev"),
            active_item=["settings", "filters", "directionality"],
        )

        def axis_labels_event(e):
            self.session.set_value(["settings", "interface", "axis_lables"], e)
            self.heatmap_y_axis_2.yaxis.axis_label = e.split("_")[0]
            self.heatmap_x_axis_2.xaxis.axis_label = e.split("_")[1]

        axis_lables = self.dropdown_select(
            "Axis Labels",
            "tooltip_y_axis_label",
            ("DNA / RNA", "DNA_RNA"),
            ("RNA / DNA", "RNA_DNA"),
            ("DNA / DNA", "DNA_DNA"),
            active_item=["settings", "interface", "axis_lables"],
            event=axis_labels_event,
        )



        def lower_bound_event(e):
            self.session.set_value(["settings", "filters", "mapping_q", "val_min"], int(e))
            self.trigger_render()

        ms_l = self.dropdown_select(
            "Mapping Quality: Lower Bound",
            "tooltip_map_q_bounds",
            (">= 0", "0"),
            *[(">= " + str(i), str(idx + 1)) for idx, i in enumerate(self.session.get_value(["map_q_thresholds"]))],
            active_item=["settings", "filters", "mapping_q", "val_min"],
            event=lower_bound_event,
        )

        def upper_bound_event(e):
            self.session.set_value(["settings", "filters", "mapping_q", "val_max"], int(e))
            self.trigger_render()
        ms_l_2 = self.dropdown_select(
            "Mapping Quality: Upper Bound",
            "tooltip_map_q_bounds",
            *[("< " + str(i), str(idx + 1)) for idx, i in enumerate(self.session.get_value(["map_q_thresholds"]))],
            ("< 255", str(len(self.session.get_value(["map_q_thresholds"])) + 1)),
            active_item=["settings", "filters", "mapping_q", "val_max"],
            event=upper_bound_event,
        )

        #ms_l = self.make_range_slider_spinner(
        #    width=SETTINGS_WIDTH,
        #    tooltip="tooltip_map_q_bounds",
        #    settings=["settings", "filters", "mapping_q"],
        #    title="Mapping Quality Bounds",
        #    sizing_mode="stretch_width",
        #)

        ibs_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_minimum_interactions",
            title="read-count adjustment",
            settings=["settings", "normalization", "min_interactions"],
            sizing_mode="stretch_width",
        )

        crs_l = self.make_range_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_color_scale_range",
            title="Color Scale Range",
            settings=["settings", "normalization", "color_range"],
            sizing_mode="stretch_width",
        )

        is_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_color_scale_log_base",
            title="Color Scale Log Base",
            settings=["settings", "normalization", "log_base"],
            sizing_mode="stretch_width",
        )

        def update_freq_event(val):
            self.session.set_value(["settings", "interface", "update_freq", "val"], val)

        ufs_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_update_frequency",
            settings=["settings", "interface", "update_freq"],
            title="Update Frequency [seconds]",  # , format="0[.]000"
            on_change=update_freq_event,
            sizing_mode="stretch_width",
        )

        rs_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_redraw_zoom",
            settings=["settings", "interface", "zoom_redraw"],
            title="Redraw if zoomed in by [%]",
            sizing_mode="stretch_width",
        )

        aas_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_add_draw_area",
            settings=["settings", "interface", "add_draw_area"],
            title="Additional Draw Area [%]",
            sizing_mode="stretch_width",
        )

        dds_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_min_diag_dist",
            settings=["settings", "filters", "min_diag_dist"],
            title="Minimum Distance from Diagonal [kbp]",
            sizing_mode="stretch_width",
        )

        def anno_size_slider_event(val):
            self.session.set_value(["settings", "interface", "anno_size", "val"], val)
            self.anno_x.width = val
            self.anno_x_axis.width = val
            self.anno_y.height = val
            self.anno_y_axis.height = val

        ass_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_anno_size",
            settings=["settings", "interface", "anno_size"],
            title=ANNOTATION_PLOT_NAME + " Size [pixel]",
            sizing_mode="stretch_width",
            on_change=anno_size_slider_event,
        )

        def raw_size_slider_event(val):
            self.session.set_value(["settings", "interface", "raw_size", "val"], val)
            self.raw_x.width = val
            self.raw_x_axis.width = val
            self.raw_y.height = val
            self.raw_y_axis.height = val

        rss2_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_raw_size",
            settings=["settings", "interface", "raw_size"],
            title=RAW_PLOT_NAME + " Size [pixel]",
            sizing_mode="stretch_width",
            on_change=raw_size_slider_event,
        )

        nb_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_max_number_of_bins",
            settings=["settings", "interface", "max_num_bins"],
            title="Max number of Bins [in thousands]",
            sizing_mode="stretch_width",
        )

        rsa_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_p_accept",
            settings=["settings", "normalization", "p_accept"],
            title="pAccept for binominal test",
            sizing_mode="stretch_width",
        )
        bsmcq_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_section_size_max_cov",
            settings=["settings", "normalization", "grid_seq_max_bin_size"],
            title="Section size max coverage [bp]",
            sizing_mode="stretch_width",
        )
        grid_seq_samples_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_section_size_max_coverage",
            settings=["settings", "normalization", "grid_seq_samples"],
            title="Number of samples",
            sizing_mode="stretch_width",
        )
        radicl_seq_samples_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_radicl_num_samples",
            settings=["settings", "normalization", "radicl_seq_samples"],
            title="Number of samples",
            sizing_mode="stretch_width",
        )
        export_coords_size = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_export_coordinate_size",
            settings=["settings", "export", "coords"],
            title="Coordinate size",
            sizing_mode="stretch_width",
        )
        axis_label_max_char = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="@todo",
            settings=["settings", "interface", "axis_label_max_char"],
            title="Maximal Character of Labels",
            sizing_mode="stretch_width",
        )
        export_contigs_size = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_export_contigs_size",
            settings=["settings", "export", "contigs"],
            title="Contig size",
            sizing_mode="stretch_width",
        )
        export_axis_size = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_export_axis_size",
            settings=["settings", "export", "axis"],
            title="Secondary Axis size",
            sizing_mode="stretch_width",
        )
        grid_seq_display_background = self.make_checkbox(
            "Display Background as Secondary Data",
            "tooltip_backg_as_sec_data",
            settings=["settings", "normalization", "grid_seq_display_background"],
        )
        radicl_seq_display_coverage = self.make_checkbox(
            "Display Coverage as Secondary Data",
            "tooltip_cov_as_sec_data",
            settings=["settings", "normalization", "radicl_seq_display_coverage"],
        )
        grid_seq_column = self.make_checkbox(
            "Compute Background for Columns",
            "tooltip_comp_backg_col",
            settings=["settings", "normalization", "grid_seq_axis_is_column"],
        )
        radicl_seq_column = self.make_checkbox(
            "Apply binominal test on Columns",
            "tooltip_comp_backg_col",
            settings=["settings", "normalization", "radicl_seq_axis_is_column"],
        )
        grid_seq_intersection = self.make_checkbox(
            "Use intersection between datasets",
            "tooltip_intersect_repl",
            settings=["settings", "normalization", "grid_seq_filter_intersection"],
        )
        grid_seq_anno = self.dropdown_select_session(
            "Annotation type",
            "tooltip_anno_type",
            ["annotation", "filterable"],
            ["settings", "normalization", "grid_seq_annotation"],
        )
        grid_seq_rna_filter_l = self.make_range_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_rna_filter",
            settings=["settings", "normalization", "grid_seq_rna_filter"],
            title="RNA reads per kbp bounds",
            sizing_mode="stretch_width",
        )
        grid_seq_dna_filter_l = self.make_range_slider_spinner(
            width=SETTINGS_WIDTH,
            tooltip="tooltip_dna_filter",
            settings=["settings", "normalization", "grid_seq_dna_filter"],
            title="Maximal DNA reads in bin bounds",
            sizing_mode="stretch_width",
        )

        group_layout = self.multi_choice_auto(
            "Dataset Name",
            "tooltip_replicates",
            [
                [["replicates", "in_group_a"], "Pool A"],
                [["replicates", "in_group_b"], "Pool B"],
            ],
            ["replicates", "list"],
            title="Primary Datapools",
            orderable=False
        )

        annos_layout = self.multi_choice_auto(
            "Annotation Name",
            "tooltip_annotations",
            [
                [["annotation", "visible_y"], "Row"],
                [["annotation", "visible_x"], "Column"],
            ],
            ["annotation", "list"],
            title="Visible Annotations",
        )

        power_tick = FuncTickFormatter(
            code="""
            if (tick / 9 >= 7)
                return Math.ceil((1 + tick % 9)) + "*10^" + Math.floor(tick / 9) + "bp";
            else if (tick / 9 >= 3)
                return Math.ceil((1 + tick % 9) * Math.pow(10, Math.floor(tick / 9)-3)) + "kbp";
            else
                return Math.ceil((1 + tick % 9) * Math.pow(10, Math.floor(tick / 9))) + "bp"; """
        )
        self.min_max_bin_size = Slider(
            start=0,
            end=1,
            value=0,
            title="Minimum Bin Size",
            format=power_tick,
            sizing_mode="fixed",
            css_classes=["tooltip", "tooltip_min_bin_size"],
            height=40,
            width=SETTINGS_WIDTH - 20,
        )

        def min_bin_size_event():
            self.session.set_value(
                ["settings", "interface", "min_bin_size", "val"],
                self.min_max_bin_size.value,
            )
            self.trigger_render()

        self.min_max_bin_size.on_change(
            "value_throttled", lambda x, y, z: min_bin_size_event()
        )

        def callback(a):
            self.min_max_bin_size.value = min(
                max(self.min_max_bin_size.value + a, self.min_max_bin_size.start),
                self.min_max_bin_size.end,
            )
            min_bin_size_event()

        button_s_up = Button(
            label="",
            css_classes=["other_button", "fa_sort_up_solid"],
            button_type="light",
            width=10,
            height=10,
        )
        button_s_up.on_click(lambda _: callback(1))
        button_s_down = Button(
            label="",
            css_classes=["other_button", "fa_sort_down_solid"],
            button_type="light",
            width=10,
            height=10,
        )
        button_s_down.on_click(lambda _: callback(-1))

        mmbs_l = row(
            [self.min_max_bin_size, column([button_s_up, button_s_down])],
            margin=DIV_MARGIN,
            width=SETTINGS_WIDTH,
        )

        self.info_status_bar = Div(
            text="Waiting for Fileinput.", sizing_mode="stretch_width"
        )
        self.info_status_bar.height = 26
        self.info_status_bar.min_height = 26
        self.info_status_bar.max_height = 26
        self.info_status_bar.height_policy = "fixed"

        status_bar_row = row(
            [self.info_status_bar],
            sizing_mode="stretch_width",
            css_classes=["top_border"],
            name="status_bar"
        )

        self.spinner = Div(
            text='<div class="lds-spinner"><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div></div>'
        )
        self.spinner.css_classes = ["fade-out"]

        norm_layout = self.multi_choice_auto(
            "Dataset name",
            "tooltip_coverage_normalization",
            [
                [["coverage", "in_column"], "Col"],
                [["coverage", "in_row"], "Row"],
            ],
            ["coverage", "list"],
            title="Secondary Datapools",
            orderable=False
        )

        anno_coords = self.dropdown_select_session(
            "Annotation Coordinate System",
            "tooltip_coordinates",
            ["annotation", "filterable"],
            ["contigs", "annotation_coordinates"],
        )
        coords_x = self.make_checkbox(
            "Use Annotation Coordinates for the columns",
            "@todo",
            settings=["settings", "filters", "anno_coords_col"],
        )
        coords_y = self.make_checkbox(
            "Use Annotation Coordinates for the rows",
            "@todo",
            settings=["settings", "filters", "anno_coords_row"],
        )

        anno_read_filter = self.dropdown_select_session(
            "Only show reads that overlap with a",
            "@todo",
            ["annotation", "filterable"],
            ["annotation", "filter"],
        )
        anno_read_filter_x = self.make_checkbox(
            "Apply Annotation filter to columns",
            "@todo",
            settings=["settings", "filters", "anno_filter_col"],
        )
        anno_read_filter_y = self.make_checkbox(
            "Apply Annotation filter to rows",
            "@todo",
            settings=["settings", "filters", "anno_filter_row"],
        )

        chrom_layout = self.multi_choice_auto(
            "Contig Name",
            "tooltip_chromosomes",
            [
                [["contigs", "displayed_on_x"], "Column"],
                [["contigs", "displayed_on_y"], "Row"],
            ],
            ["contigs", "list"],
            title="Active Contigs",
        )

        multiple_anno_per_bin = self.dropdown_select(
            "Multiple Annotations in Bin",
            "tooltip_multiple_annotations_in_bin",
            ("Combine region from first to last annotation", "combine"),
            ("Use first annotation in Bin", "first"),
            (
                "Use one prioritized annotation. (stable while zoom- and pan-ing)",
                "max_fac_pow_two",
            ),
            (
                "Increase number of bins to match number of annotations (might be slow)",
                "force_separate",
            ),
            active_item=["settings", "filters", "multiple_annos_in_bin"],
        )
        multiple_bin_per_anno = self.dropdown_select(
            "Multiple Bins for Annotation",
            "tooltip_multiple_bin_for_anno",
            ("Stretch one bin over entire annotation", "stretch"),
            ("Show several bins for the annotation", "separate"),
            ("Make all annotations size 1", "squeeze"),
            active_item=["settings", "filters", "anno_in_multiple_bins"],
        )

        export_button = Button(
            label="Export",
            width=SETTINGS_WIDTH,
            sizing_mode="fixed",
            css_classes=["other_button", "tooltip", "tooltip_export"],
            height=DROPDOWN_HEIGHT,
        )

        def exp_event(x):
            self.do_export()

        export_button.on_click(exp_event)

        export_format = self.dropdown_select(
            "Format",
            "tooltip_export_format",
            ("TSV-file", "tsv"),
            ("SVG-picture", "svg"),
            ("PNG-picture", "png"),
            active_item=["settings", "export", "export_format"],
        )

        # export_full = self.make_checkbox("Export full matrix instead", "tooltip_full_matrix",
        #                                    settings=["settings", "export", "do_export_full"])

        export_label = Div(
            text="Output Prefix:", css_classes=["tooltip", "tooltip_export_prefix"]
        )
        export_label.margin = DIV_MARGIN
        self.export_file = TextInput(
            css_classes=["tooltip", "tooltip_export_prefix"],
            height=DEFAULT_TEXT_INPUT_HEIGHT,
            width=SETTINGS_WIDTH,
        )

        def export_file_event(_1, _2, _3):
            self.session.set_value(
                ["settings", "export", "prefix"], self.export_file.value
            )

        self.export_file.on_change("value", export_file_event)

        self.low_color = ColorPicker(
            title="Color Low",
            css_classes=["tooltip", "tooltip_color_low"],
            height=DEFAULT_TEXT_INPUT_HEIGHT * 2,
        )
        self.high_color = ColorPicker(
            title="Color High",
            css_classes=["tooltip", "tooltip_color_high"],
            height=DEFAULT_TEXT_INPUT_HEIGHT * 2,
        )

        def color_event_low(_1, _2, _3):
            self.session.set_value(
                ["settings", "interface", "color_low"], self.low_color.color
            )
            self.trigger_render()

        def color_event_high(_1, _2, _3):
            self.session.set_value(
                ["settings", "interface", "color_high"], self.high_color.color
            )
            self.trigger_render()

        self.low_color.on_change("color", color_event_low)
        self.high_color.on_change("color", color_event_high)

        with pkg_resources.open_text("biosmoother", "VERSION") as in_file:
            self.biosmoother_version = in_file.readlines()[0][:-1]

        version_info = Div(
            text="BioSmoother "
            + self.biosmoother_version
            + "<br>LibSps Version: "
            + Quarry.get_libSps_version()
        )
        index_info = Div(
            text="Index path:" + os.environ["biosmoother_index_path"] if "biosmoother_index_path" in os.environ else "unknown"
        )

        self.color_layout = row(
            [self.make_color_figure(["#000000"])],
            css_classes=["tooltip", "tooltip_color_layout"],
        )

        quick_configs = [self.config_row("default", lock_name=True)]
        for idx in range(1, 7):
            quick_configs.append(self.config_row(idx))

        SYM_WIDTH = 18
        SYM_CSS = ["other_button"]
        reset_session = Button(
            label="",
            css_classes=SYM_CSS + ["fa_reset"],
            width=SYM_WIDTH,
            height=25,
            sizing_mode="fixed",
            button_type="light",
            align="center",
        )

        def reset_event():
            path = None
            if "biosmoother_index_path" in os.environ:
                if os.path.exists(os.environ["biosmoother_index_path"]):
                    path = os.environ["biosmoother_index_path"]
                if os.path.exists(os.environ["biosmoother_index_path"] + ".biosmoother_index/"):
                    path = os.environ["biosmoother_index_path"] + ".biosmoother_index/"
            if not path is None:
                with open(path + "/default_session.json", "r") as f:
                    default_session = json.load(f)
                    default_session["settings"] = self.session.get_value(["settings"])
            self.session.set_session(default_session)
            self.do_config()
            self.trigger_render()

        reset_session.on_click(reset_event)

        self.ticker_x = ExtraTicksTicker(extra_ticks=[])
        self.ticker_x_2 = IntermediateTicksTicker(extra_ticks=[])
        self.ticker_y = ExtraTicksTicker(extra_ticks=[])
        self.ticker_y_2 = IntermediateTicksTicker(extra_ticks=[])

        def get_formatter_tick():
            return FuncTickFormatter(
                args={"screen_starts": [], "index_starts": [], "genome_end": 0, "dividend": 1},
                code="""
                            function numberWithCommas(x) {
                                return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                            }
                            if(tick < 0 || tick >= genome_end)
                                return "n/a";
                            var idx = 0;
                            while(screen_starts[idx + 1] <= tick)
                                idx += 1;
                            var tick_pos = dividend * (tick - screen_starts[idx] + index_starts[idx]);
                            var tick_label = "";
                            if(tick_pos == 0)
                                tick_label = "0 bp"
                            else if(tick_pos % 1000000 == 0)
                                tick_label = numberWithCommas(tick_pos / 1000000) + " mbp";
                            else if (tick_pos % 1000 == 0)
                                tick_label = numberWithCommas(tick_pos / 1000) + " kbp";
                            else
                                tick_label = numberWithCommas(tick_pos) + " bp";
                            return tick_label;
                        """,
            )

        def get_formatter_chr():
            return FuncTickFormatter(
                args={
                    "contig_starts": [],
                    "genome_end": 0,
                    "contig_names": []
                },
                code="""
                            if(tick < 0 || tick >= genome_end)
                                return "n/a";
                            var idx = 0;
                            while(idx + 1 < contig_starts.length && contig_starts[idx + 1] <= tick)
                                idx += 1;
                            return contig_names[idx];
                        """,
            )

        self.tick_formatter_x = get_formatter_tick()
        self.tick_formatter_x_2 = get_formatter_chr()
        self.tick_formatter_y = get_formatter_tick()
        self.tick_formatter_y_2 = get_formatter_chr()

        self.heatmap_x_axis.xaxis[0].formatter = self.tick_formatter_x
        self.heatmap_x_axis_2.xaxis[0].formatter = self.tick_formatter_x_2
        self.heatmap_y_axis.yaxis[0].formatter = self.tick_formatter_y
        self.heatmap_y_axis_2.yaxis[0].formatter = self.tick_formatter_y_2

        self.undo_button = Button(
            label="",
            css_classes=SYM_CSS + ["fa_page_previous_solid"],
            width=SYM_WIDTH,
            height=SYM_WIDTH,
            sizing_mode="fixed",
            button_type="light",
            align="center",
        )

        def undo_event():
            self.session.undo()
            self.do_config()
            self.trigger_render()

        self.undo_button.on_click(undo_event)
        self.redo_button = Button(
            label="",
            css_classes=SYM_CSS + ["fa_page_next_solid"],
            width=SYM_WIDTH,
            height=SYM_WIDTH,
            sizing_mode="fixed",
            button_type="light",
            align="center",
        )

        def redo_event():
            self.session.redo()
            self.do_config()
            self.trigger_render()

        self.redo_button.on_click(redo_event)

        self.heatmap_x_axis_2.xaxis.ticker = self.ticker_x_2
        self.heatmap_x_axis_2.xaxis.axis_line_color = None
        self.heatmap_x_axis_2.xaxis.axis_label_text_font = "monospace"
        self.heatmap_x_axis_2.xaxis.major_tick_line_color = None
        self.heatmap_x_axis_2.xaxis.major_tick_out = 0
        self.heatmap_x_axis_2.y_range.start = 1
        self.heatmap_x_axis_2.y_range.end = 2
        self.heatmap_x_axis_2.background_fill_color = None
        self.heatmap_x_axis_2.outline_line_color = None
        self.heatmap_x_axis_2.ygrid.grid_line_alpha = 0.0

        self.heatmap_x_axis_3.xaxis.ticker = self.ticker_x
        self.heatmap_x_axis_3.xaxis.major_label_text_font_size = '0pt'
        self.heatmap_x_axis_3.xaxis.minor_tick_line_color = None
        self.heatmap_x_axis_3.y_range.start = 1
        self.heatmap_x_axis_3.y_range.end = 2
        self.heatmap_x_axis_3.background_fill_color = None
        self.heatmap_x_axis_3.outline_line_color = None
        self.heatmap_x_axis_3.ygrid.grid_line_alpha = 0.0

        self.heatmap_y_axis_2.yaxis.ticker = self.ticker_y_2
        self.heatmap_y_axis_2.yaxis.axis_line_color = None
        self.heatmap_y_axis_2.yaxis.major_tick_line_color = None
        self.heatmap_y_axis_2.yaxis.major_tick_out = 0
        self.heatmap_y_axis_2.x_range.start = 1
        self.heatmap_y_axis_2.x_range.end = 2
        self.heatmap_y_axis_2.background_fill_color = None
        self.heatmap_y_axis_2.outline_line_color = None
        self.heatmap_y_axis_2.xgrid.grid_line_alpha = 0.0

        self.heatmap_y_axis_3.yaxis.ticker = self.ticker_y
        self.heatmap_y_axis_3.yaxis.major_label_text_font_size = '0pt'
        self.heatmap_y_axis_3.yaxis.minor_tick_line_color = None
        self.heatmap_y_axis_3.x_range.start = 1
        self.heatmap_y_axis_3.x_range.end = 2
        self.heatmap_y_axis_3.background_fill_color = None
        self.heatmap_y_axis_3.outline_line_color = None
        self.heatmap_y_axis_3.xgrid.grid_line_alpha = 0.0

        for plot in [self.heatmap, self.raw_y, self.anno_y, self.heatmap_x_axis]:
            plot.xgrid.ticker = self.ticker_x
            plot.xaxis.major_label_text_align = "left"
            plot.xaxis.ticker.min_interval = 1
        for plot in [self.heatmap, self.raw_x, self.anno_x, self.heatmap_y_axis]:
            plot.ygrid.ticker = self.ticker_y
            plot.yaxis.major_label_text_align = "right"
            plot.yaxis.ticker.min_interval = 1

        log_div = Div(text="Log:", sizing_mode="stretch_width")
        self.log_div = Div(
            css_classes=["scroll_y2"],
            width=SETTINGS_WIDTH,
            max_height=400,
            sizing_mode="stretch_height",
        )

        self.area_range = TextInput(
            value="n/a",
            width=SETTINGS_WIDTH * 2,
            height=26,
            css_classes=["tooltip", "tooltip_area_range", "text_align_center"],
        )
        self.area_range.on_change("value", lambda x, y, z: self.parse_area_range())
        tools_bar = row(
            [
                self.spinner,
                self.undo_button,
                self.redo_button,
                self.area_range,
                tool_bar,
                reset_session,
            ],
            css_classes=["bottom_border"],
            name="tools_bar",
        )
        tools_bar.height = 40
        tools_bar.min_height = 40
        tools_bar.height_policy = "fixed"

        if bin.global_variables.no_save:
            export_panel = [
                Div(
                    text="This instance of biosmoother has been configured not to allow saving files on the server, so the Export tab has been disabled. Otherwise you could use this tab to export your raw data in tsv format, or create svg pictures from your data.",
                    sizing_mode="stretch_width",
                )
            ]
        else:
            export_panel = [
                export_label,
                self.export_file,
                export_format,
                export_coords_size,
                export_contigs_size,
                export_axis_size,
                export_button,
            ]

        do_v4c_col = self.make_checkbox(
            "Compute for columns",
            "tooltip_v4c_do_column",
            settings=["settings", "interface", "v4c", "do_col"],
        )

        v4c_col_label = Div(
            text="Column Range", css_classes=["tooltip", "tooltip_v4c_column"]
        )
        v4c_col_label.margin = DIV_MARGIN
        self.v4c_col = TextInput(
            css_classes=["tooltip", "tooltip_v4c_column"],
            height=DEFAULT_TEXT_INPUT_HEIGHT,
            width=SETTINGS_WIDTH,
        )
        self.v4c_col.on_change("value", lambda x, y, z: self.parse_v4c())

        do_v4c_row = self.make_checkbox(
            "Compute for rows",
            "tooltip_v4c_do_row",
            settings=["settings", "interface", "v4c", "do_row"],
        )
        v4c_row_label = Div(
            text="Row Range", css_classes=["tooltip", "tooltip_v4c_column"]
        )
        v4c_row_label.margin = DIV_MARGIN
        self.v4c_row = TextInput(
            css_classes=["tooltip", "tooltip_v4c_column"],
            height=DEFAULT_TEXT_INPUT_HEIGHT,
            width=SETTINGS_WIDTH,
        )
        self.v4c_row.on_change("value", lambda x, y, z: self.parse_v4c())

        _settings = self.make_tabs(
            tabs=[
                self.make_panel(
                    "File",
                    children=[
                        Spacer(height=5),
                        self.make_tabs(
                            tabs=[
                                self.make_panel("Presetting", "", [*quick_configs]),
                                self.make_panel("Export", "", export_panel),
                                self.make_panel(
                                    "Info", "", [version_info, index_info, log_div, 
                                                 self.log_div
                                                 ]
                                ),
                            ]
                        ),
                    ],
                    inner=False,
                ),
                self.make_panel(
                    "Normalize",
                    children=[
                        Spacer(height=5),
                        normalization,
                        normalization_cov,
                        self.make_tabs(
                            tabs=[
                                self.make_panel(
                                    "Binominal Test",
                                    "",
                                    [
                                        rsa_l,
                                        radicl_seq_display_coverage,
                                        radicl_seq_column,
                                        radicl_seq_samples_l,
                                    ],
                                ),
                                self.make_panel(
                                    "Dist. Dep. Dec.",
                                    "",
                                    [
                                        ddd,
                                        ddd_show,
                                        ddd_sam_l,
                                        ddd_ex_l,
                                        self.dist_dep_dec_plot,
                                    ],
                                ),
                                self.make_panel(
                                    "Associated slices",
                                    "",
                                    [
                                        grid_seq_samples_l,
                                        bsmcq_l,
                                        grid_seq_column,
                                        grid_seq_anno,
                                        grid_seq_display_background,
                                        grid_seq_intersection,
                                        grid_seq_rna_filter_l,
                                        self.ranked_columns,
                                        grid_seq_dna_filter_l,
                                        self.ranked_rows,
                                    ],
                                ),
                                self.make_panel("ICE", "", [ice_sparse_filter, ice_num_samples, 
                                                            ice_show_bias, ice_local]),
                            ]
                        ),
                    ],
                    inner=False,
                ),
                self.make_panel(
                    "Filter",
                    children=[
                        Spacer(height=5),
                        self.make_tabs(
                            tabs=[
                                self.make_panel(
                                    "Datapools",
                                    "",
                                    [
                                        in_group,
                                        betw_group,
                                        group_layout,
                                        ibs_l,
                                        norm_layout,
                                    ],
                                ),
                                self.make_panel(
                                    "Mapping",
                                    "",
                                    [
                                        ms_l,
                                        ms_l_2,
                                        incomp_align_layout,
                                        multi_mapping,
                                        directionality,
                                    ],
                                ),
                                self.make_panel(
                                    "Coordinates",
                                    "",
                                    [
                                        dds_l,
                                        anno_coords,
                                        coords_x,
                                        coords_y,
                                        symmetrie,
                                        chrom_layout,
                                    ],
                                ),
                                self.make_panel(
                                    "Annotations",
                                    "",
                                    [
                                        annos_layout,
                                        multiple_anno_per_bin,
                                        multiple_bin_per_anno,
                                        anno_read_filter,
                                        anno_read_filter_x,
                                        anno_read_filter_y,
                                    ],
                                ),
                            ]
                        ),
                    ],
                    inner=False,
                ),
                self.make_panel(
                    "View",
                    children=[
                        Spacer(height=5),
                        self.make_tabs(
                            tabs=[
                                self.make_panel(
                                    "Color",
                                    "",
                                    [
                                        self.color_layout,
                                        crs_l,
                                        is_l,
                                        color_scale,
                                        color_picker,
                                        self.low_color,
                                        self.high_color,
                                    ],
                                ),
                                self.make_panel(
                                    "Panels",
                                    "",
                                    [show_hide, ass_l, rss2_l, axis_lables, axis_label_max_char],
                                ),
                                self.make_panel(
                                    "Bins",
                                    "",
                                    [
                                        nb_l,
                                        mmbs_l,
                                        square_bins,
                                        power_ten_bin,
                                        last_bin_in_contig,
                                        contig_smaller_than_bin,
                                    ],
                                ),
                                self.make_panel(
                                    "Virtual4C",
                                    "",
                                    [
                                        do_v4c_col,
                                        v4c_col_label,
                                        self.v4c_col,
                                        do_v4c_row,
                                        v4c_row_label,
                                        self.v4c_row,
                                    ],
                                ),
                                self.make_panel("Rendering", "", [ufs_l, rs_l, aas_l, do_redraw, render_now]),
                            ]
                        ),
                    ],
                    inner=False,
                ),
            ],
            outer=True
        )

        _settings_n_info = column([Spacer(height=5), _settings])
        _settings_n_info.width = SETTINGS_WIDTH + 25
        _settings_n_info.width_policy = "fixed"

        self.hidable_plots.append((_settings_n_info, ["tools"]))
        self.settings_row = row(
            [
                Spacer(sizing_mode="stretch_both"),
                _settings_n_info,
                self.reshow_settings(),
            ],
            name="settings_row",
            sizing_mode="stretch_height",
        )
        self.settings_row.width = SETTINGS_WIDTH + 25
        self.settings_row.width_policy = "fixed"

        quit_ti = TextInput(value="keepalive", name="quit_ti", visible=False)

        def close_server(x, y, z):
            if bin.global_variables.keep_alive:
                if not bin.global_variables.quiet:
                    print("session exited; keeping server alive")
            else:
                if not bin.global_variables.quiet:
                    print("closing server since session exited")
                if not bin.global_variables.no_save:
                    self.session.save_session()
                sys.exit()

        quit_ti.on_change("value", close_server)

        communication = row([quit_ti], name="communication")
        communication.visible = False

        self.curdoc.add_root(self.heatmap)
        self.curdoc.add_root(self.heatmap_y_axis)
        self.curdoc.add_root(self.heatmap_y_axis_2)
        self.curdoc.add_root(self.heatmap_y_axis_3)
        self.curdoc.add_root(self.heatmap_x_axis)
        self.curdoc.add_root(self.heatmap_x_axis_2)
        self.curdoc.add_root(self.heatmap_x_axis_3)
        self.curdoc.add_root(self.anno_x)
        self.curdoc.add_root(self.anno_x_axis)
        self.curdoc.add_root(self.raw_x)
        self.curdoc.add_root(self.raw_x_axis)
        self.curdoc.add_root(self.anno_y)
        self.curdoc.add_root(self.anno_y_axis)
        self.curdoc.add_root(self.raw_y)
        self.curdoc.add_root(self.raw_y_axis)
        self.curdoc.add_root(self.settings_row)
        self.curdoc.add_root(communication)
        self.curdoc.add_root(status_bar_row)
        self.curdoc.add_root(tools_bar)

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

    def print(self, s):
        if not bin.global_variables.quiet:
            print(s)
        self.log_div_text += s.replace("\n", "<br>") + "<br>"
        # self.log_div_text = self.log_div_text[-5000:]

    def update_log_div(self):
        def callback():
            self.log_div.text = self.log_div_text

        self.curdoc.add_next_tick_callback(callback)

    def print_status(self, s):
        self.print(s)

        def callback():
            self.info_status_bar.text = s.replace("\n", " | ")

        self.curdoc.add_next_tick_callback(callback)

    def get_readable_bin_size(self):
        w_bin, h_bin = self.session.get_bin_size(self.print)

        def readable_display(l):
            def add_commas(x):
                return "{:,}".format(x)

            if l % 1000000 == 0:
                return str(add_commas(l // 1000000)) + "mbp"
            elif l % 1000 == 0:
                return str(add_commas(l // 1000)) + "kbp"
            else:
                return str(add_commas(l)) + "bp"

        return readable_display(w_bin) + " x " + readable_display(h_bin)

    @gen.coroutine
    @without_document_lock
    def render(self, zoom_in_render):
        def unlocked_task():
            def cancelable_task():
                def callback():
                    self.spinner.css_classes = ["fade-in"]

                self.curdoc.add_next_tick_callback(callback)

                start_time = datetime.now()

                # @continue_here @fixme type must be number but is null json exception from cpp
                self.session.update_cds(self.print)

                d_heatmap = self.session.get_heatmap(self.print)

                raw_data_x = self.session.get_tracks(False, self.print)
                raw_data_y = self.session.get_tracks(True, self.print)
                min_max_tracks_x = self.session.get_min_max_tracks(False, self.print)
                min_max_tracks_y = self.session.get_min_max_tracks(True, self.print)

                d_anno_x = self.session.get_annotation(False, self.print)
                d_anno_y = self.session.get_annotation(True, self.print)
                displayed_annos_x = self.session.get_displayed_annos(False, self.print)
                if len(displayed_annos_x) == 0:
                    displayed_annos_x.append("")
                displayed_annos_y = self.session.get_displayed_annos(True, self.print)
                if len(displayed_annos_y) == 0:
                    displayed_annos_y.append("")

                b_col = self.session.get_background_color(self.print)

                render_area = self.session.get_drawing_area(self.print)

                canvas_size_x, canvas_size_y = self.session.get_canvas_size(self.print)
                tick_list_x = self.session.get_tick_list(True, self.print)
                tick_list_y = self.session.get_tick_list(False, self.print)
                ticks_x = self.session.get_ticks(True, self.print)
                ticks_y = self.session.get_ticks(False, self.print)
                contig_ticks_x = self.session.get_contig_ticks(True, self.print)
                contig_ticks_y = self.session.get_contig_ticks(False, self.print)

                palette = self.session.get_palette(self.print)

                ranked_slice_x = self.session.get_ranked_slices(False, self.print)
                ranked_slice_y = self.session.get_ranked_slices(True, self.print)
                if self.session.get_value(["settings", "normalization", "ddd_show"]):
                    dist_dep_dec_plot_data = self.session.get_decay(self.print)
                else:
                    dist_dep_dec_plot_data = {
                        "chr": [],
                        "color": [],
                        "xs": [],
                        "ys": [],
                    }

                error = self.session.get_error()
                error_text = "None" if len(error) == 0 else error.replace("\n", "; ")
                end_time = datetime.now()

                @gen.coroutine
                def callback():
                    self.curdoc.hold()
                    if not bin.global_variables.quiet:
                        self.print("ERROR: " + error_text)
                    self.color_layout.children = [
                        self.make_color_figure(palette)
                    ]

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

                    end_text = (
                        "Rendering Done.\nCurrent Bin Size: "
                        + self.get_readable_bin_size()
                        + ".\nRuntime: "
                        + str(end_time - start_time)
                        + ".\nDisplaying "
                        + str(len(d_heatmap["color"]))
                        + " bins."
                    )

                    self.raw_x_axis.xaxis.bounds = (
                        min_max_tracks_x[0],
                        min_max_tracks_x[1],
                    )
                    self.raw_y_axis.yaxis.bounds = (
                        min_max_tracks_y[0],
                        min_max_tracks_y[1],
                    )

                    def set_bounds(
                        plot, left=None, right=None, top=None, bottom=None, color=None
                    ):
                        ra = self.plot_render_area(plot)
                        ra.left = render_area[0] if left is None else left
                        ra.bottom = render_area[1] if bottom is None else bottom
                        ra.right = render_area[2] if right is None else right
                        ra.top = render_area[3] if top is None else top
                        if not color is None:
                            ra.fill_color = color

                    set_bounds(
                        self.raw_x, left=min_max_tracks_x[0], right=min_max_tracks_x[1]
                    )
                    set_bounds(
                        self.raw_y, bottom=min_max_tracks_y[0], top=min_max_tracks_y[1]
                    )
                    set_bounds(self.anno_x, left=0, right=len(displayed_annos_x))
                    set_bounds(self.anno_y, bottom=0, top=len(displayed_annos_y))

                    set_bounds(self.heatmap, color=b_col)

                    self.heatmap_data.data = d_heatmap
                    self.raw_data_x.data = raw_data_x
                    x_visible = len(raw_data_x["values"]) > 0
                    self.raw_x.visible = self.show_hide["raw"] and x_visible
                    self.raw_x_axis.visible = self.show_hide["raw"] and x_visible
                    self.raw_data_y.data = raw_data_y
                    y_visible = len(raw_data_y["values"]) > 0
                    self.raw_y.visible = self.show_hide["raw"] and y_visible
                    self.raw_y_axis.visible = self.show_hide["raw"] and y_visible

                    self.anno_x.x_range.factors = displayed_annos_x
                    self.anno_y.y_range.factors = displayed_annos_y[::-1]

                    self.anno_x_data.data = d_anno_x
                    self.anno_y_data.data = d_anno_y
                    self.anno_x.visible = len(d_anno_x["anno_name"]) > 0 and self.show_hide["annotation"]
                    self.anno_x_axis.visible =self.anno_x.visible
                    self.anno_y.visible = len(d_anno_y["anno_name"]) > 0 and self.show_hide["annotation"]
                    self.anno_y_axis.visible =self.anno_y.visible

                    self.heatmap.x_range.reset_start = 0
                    self.heatmap.x_range.reset_end = canvas_size_x
                    self.heatmap.y_range.reset_start = 0
                    self.heatmap.y_range.reset_end = canvas_size_y

                    self.ticker_x.extra_ticks = tick_list_x
                    self.ticker_x_2.extra_ticks = tick_list_x
                    self.ticker_y.extra_ticks = tick_list_y
                    self.ticker_y_2.extra_ticks = tick_list_y

                    self.tick_formatter_x.args = ticks_x
                    self.tick_formatter_x_2.args = contig_ticks_x
                    self.tick_formatter_y.args = ticks_y
                    self.tick_formatter_y_2.args = contig_ticks_y

                    self.ranked_columns_data.data = ranked_slice_y
                    self.ranked_rows_data.data = ranked_slice_x
                    self.dist_dep_dec_plot_data.data = dist_dep_dec_plot_data

                    self.set_area_range()

                    for plot in [
                        self.heatmap,
                        self.raw_y,
                        self.anno_y,
                        self.heatmap_x_axis,
                        self.heatmap_x_axis_3,
                    ]:
                        plot.xgrid.bounds = (0, canvas_size_x)
                        plot.xaxis.bounds = (0, canvas_size_x)
                    for plot in [
                        self.heatmap,
                        self.raw_x,
                        self.anno_x,
                        self.heatmap_y_axis,
                        self.heatmap_y_axis_3,
                    ]:
                        plot.ygrid.bounds = (0, canvas_size_y)
                        plot.yaxis.bounds = (0, canvas_size_y)

                    self.curdoc.unhold()
                    self.print_status(end_text + " | Errors: " + error_text)
                    self.curdoc.add_timeout_callback(
                        lambda: self.render_callback(),
                        self.session.get_value(
                            ["settings", "interface", "update_freq", "val"]
                        )
                        * 1000,
                    )
                self.curdoc.add_next_tick_callback(callback)
                return True

            while cancelable_task() is None:
                pass

            def callback():
                self.spinner.css_classes = ["fade-out"]
                if not bin.global_variables.no_save:
                    self.session.save_session()

            self.curdoc.add_next_tick_callback(callback)

        self.undo_button.disabled = not self.session.has_undo()
        self.undo_button.css_classes = [
            "other_button",
            "fa_page_previous"
            if self.undo_button.disabled
            else "fa_page_previous_solid",
        ]
        self.redo_button.disabled = not self.session.has_redo()
        self.redo_button.css_classes = [
            "other_button",
            "fa_page_next" if self.redo_button.disabled else "fa_page_next_solid",
        ]
        yield executor.submit(unlocked_task)

    def trigger_render(self):
        self.session.cancel()
        self.force_render = True

    def render_callback(self):
        # @todo update contig name cycling
        self.update_log_div()
        if not self.session is None:
            if not None in (
                self.heatmap.x_range.start,
                self.heatmap.x_range.end,
                self.heatmap.y_range.start,
                self.heatmap.y_range.end,
            ):
                curr_area = (
                    self.heatmap.x_range.start,
                    self.heatmap.y_range.start,
                    self.heatmap.x_range.end,
                    self.heatmap.y_range.end,
                )
                curr_area_size = (curr_area[2] - curr_area[0]) * (
                    curr_area[3] - curr_area[1]
                )
                min_change = (
                    1
                    - self.session.get_value(
                        ["settings", "interface", "zoom_redraw", "val"]
                    )
                    / 100
                )
                zoom_in_render = False
                if (
                    ( ( curr_area_size / self.curr_area_size < min_change
                        or MainLayout.area_outside(self.last_drawing_area, curr_area) )
                      and self.session.get_value(["settings", "interface", "do_redraw"]) )
                    or self.force_render
                ):
                    if curr_area_size / self.curr_area_size < min_change:
                        self.print_status("rendering due to zoom in.")
                        zoom_in_render = True
                    elif self.force_render:
                        self.print_status("rendering due to parameter change.")
                    elif MainLayout.area_outside(self.last_drawing_area, curr_area):
                        self.print_status("rendering due to pan or zoom out.")
                    else:
                        self.print_status("rendering.")
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
                        self.last_drawing_area = self.session.get_drawing_area(
                            self.print
                        )
                        self.render(zoom_in_render)

                    self.curdoc.add_next_tick_callback(callback)
                    return

            self.curdoc.add_timeout_callback(
                lambda: self.render_callback(),
                self.session.get_value(
                    ["settings", "interface", "update_freq", "val"]
                )
                * 1000,
            )
        else:
            self.curdoc.add_timeout_callback(lambda: self.render_callback(), 1000)

    def set_root(self):
        self.curdoc.title = "BioSmoother"
        self.force_render = True
        self.do_config()
        self.render_callback()
