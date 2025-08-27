__author__ = "Markus Schmidt"
__email__ = "Markus.Schmidt@lmu.de"

from bokeh.layouts import grid, row, column  # pyright: ignore missing import
from bokeh.plotting import figure, curdoc  # pyright: ignore missing import
from bokeh.models import (  # pyright: ignore missing import
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
    CustomJS,
    CustomJSHover,
    FileInput,
)
from bokeh.transform import jitter  # pyright: ignore missing import
import math
from tornado import gen  # pyright: ignore missing import
from bokeh.document import without_document_lock  # pyright: ignore missing import
import os
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from bokeh.models.tickers import (
    AdaptiveTicker,
    LogTicker,
)  # pyright: ignore missing import
from libbiosmoother import (
    Quarry,
    export_tsv,
    export_png,
    export_svg,
    get_tsv,
    get_png,
    get_svg,
    open_default_json,
    open_descriptions_json,
    open_button_names_json
)  # pyright: ignore missing import
import json
from bin.figure_maker import (  # pyright: ignore missing import
    FigureMaker,
    DROPDOWN_HEIGHT,
    FONT,
)  # pyright: ignore missing import
from bin.extra_ticks_ticker import *  # pyright: ignore missing import
import bin.global_variables  # pyright: ignore missing import
import numpy as np  # pyright: ignore missing import
import base64

try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources  # pyright: ignore missing import
from pathlib import Path
from pybase64 import b64decode
import io
import re

SETTINGS_WIDTH = 400
BUTTON_HEIGHT = 30
DEFAULT_SIZE = 50
ANNOTATION_PLOT_NAME = "Annotation panel"
RAW_PLOT_NAME = "Secondary data panel"

DIV_MARGIN = (5, 5, 0, 5)
BTN_MARGIN = (3, 3, 3, 3)
BTN_MARGIN_2 = (3, 3, 3, 3)

CONFIG_FILE_VERSION = 0.5

DEFAULT_TEXT_INPUT_HEIGHT = 30

executor = ThreadPoolExecutor(max_workers=1)

biosmoother_home_folder = str(Path.home()) + "/.biosmoother"

JS_UPDATE_LAYOUT = """
    layout_needed=true;
    setTimeout(function(){
        if(layout_needed){
            window.dispatchEvent(new Event('resize'));
            layout_needed=false;
        }
    }, 1);
"""

JS_HOVER = """
    return source.data.chr[value] + " " + source.data.index_left[value] + " .. " + source.data.index_right[value];
"""

JS_DOWNLOAD = """
    if(decode_to_bytes){
        filetext = new Uint8Array(atob(filetext).split('').map(char => char.charCodeAt(0)));
    }

    const blob = new Blob([filetext], { type: filetype })

    //addresses IE
    if (navigator.msSaveBlob) {
        navigator.msSaveBlob(blob, filename)
    } else {
        const link = document.createElement('a')
        link.href = URL.createObjectURL(blob)
        link.download = filename
        link.target = '_blank'
        link.style.visibility = 'hidden'
        link.dispatchEvent(new MouseEvent('click'))
    }
"""


if True:
    UP_ASCI = "^"
    DOWN_ASCI = "v"
    UNSELECTED_ASCI = "[ ]"
    SELECTED_ASCI = "[X]"
    SOME_SELECTED_ASCI = "[.]"
else:
    SELECTED_ASCI = "🞕"
    UNSELECTED_ASCI = "☐"
    SOME_SEL_ASCIECTED_ASCI = "·"
    UP_ASCI = "▲"
    DOWN_ASCI = "▼"

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

    def dropdown_select(
        self,
        *options,
        active_item=None,
        event=None,
        trigger_render=True
    ):
        self.in_descriptions_json(active_item)
        tooltip = "tooltip__" + "__".join(active_item)
        title = self.get_button_name(active_item)

        if event is None:

            def default_event(e):
                self.session.set_value(active_item, e)
                if trigger_render:
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
        self, session_key, active_item, add_keys=[], event=None
    ):
        self.in_descriptions_json(active_item)
        tooltip = "tooltip__" + "__".join(active_item)
        title = self.get_button_name(active_item)

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
        checkboxes,
        session_key=None,
        callback=None,
        orderable=True,
        renamable=False,
    ):
        self.in_descriptions_json(checkboxes[0][0])
        tooltip = "tooltip__" + "__".join(checkboxes[0][0])
        title = self.get_button_name(checkboxes[0][0])

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

        my_id = self.next_element_id

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
        css_classes_add_on = []
        columns = make_columns()
        if orderable:
            css_classes_add_on.append("table_col_1_clickable")
            css_classes_add_on.append("table_col_2_clickable")
        for idx in range(len(columns)):
            css_classes_add_on.append("table_col_" + str(idx + 2 + (2 if orderable else 0)) + "_clickable")
        data_table = DataTable(
            source=ColumnDataSource(make_source()),
            columns=columns,
            editable=True,
            autosize_mode="fit_columns",
            index_position=None,
            width=SETTINGS_WIDTH - 10,
            tags=["blub"],
            height=200,
            sortable=False,
            css_classes=[
                "multichoice_element_id_" + str(self.next_element_id),
                "white_background",
            ] + css_classes_add_on,
        )

        source_code = """
            var grids = document.getElementsByClassName(element_id)[0].getElementsByClassName('grid-canvas');
            for (var k = 0,kmax = grids.length; k < kmax; k++){
                if(grids[k].outerHTML.includes('active')){
                    var grid = grids[k].children;
                    for (var i = 0,max = grid.length; i < max; i++){
                        if (grid[i].outerHTML.includes('active')){
                            for (var j = 0, jmax = grid[i].children.length; j < jmax; j++)
                                if(grid[i].children[j].outerHTML.includes('active')) { 
                                    select_ret.value = grid[i].children[0].textContent + " " + grid[i].children[j].className + " " + element_id;
                                }
                        }
                    }
                }
            }
        """
        js_callback = CustomJS(
            args={
                "select_ret": select_ret,
                "element_id": "multichoice_element_id_" + str(self.next_element_id),
            },
            code=source_code,
        )
        self.next_element_id += 1

        self.reset_options[my_id] = [{}, []]

        filter_t_in = TextInput(placeholder="filter...", width=170)
        def matches_filter(filter_t_in, fx):
            if len(filter_t_in.value) == 0:
                return True
            is_inv_filter = filter_t_in.value.startswith("!")
            split_filter = filter_t_in.value.lower()[1 if is_inv_filter else 0:].split("*")
            idx = 0
            for s in split_filter:
                idx = fx.find(s, idx)
                if idx == -1:
                    return is_inv_filter
                idx += len(s)
            return not is_inv_filter

        def set_options(labels, active_dict):
            self.reset_options[my_id] = [active_dict, labels]
            source = make_source()
            if len(labels) > 1:
                source["idx"].append("")
                if orderable:
                    source["up"].append("")
                    source["down"].append("")
                source["names"].append("select all")
                for _, n in checkboxes:
                    bools = [name in active_dict[n] for name in labels if matches_filter(filter_t_in, name.lower())]
                    source[n].append(
                        SELECTED_ASCI
                        if all(bools)
                        else (UNSELECTED_ASCI if all(not b for b in bools) else SOME_SELECTED_ASCI)
                    )
            for idx, name in enumerate(labels):
                if matches_filter(filter_t_in, name.lower()):
                    source["idx"].append(str(idx + 1))
                    if orderable:
                        source["up"].append(UP_ASCI if idx > 0 else "")
                        source["down"].append(DOWN_ASCI if idx < len(labels) - 1 else "")
                    source["names"].append(name)
                    for _, n in checkboxes:
                        source[n].append(SELECTED_ASCI if name in active_dict[n] else UNSELECTED_ASCI)

            data_table.source.data = source
            data_table.frozen_rows = 1 if len(labels) > 1 else 0
            # data_table.columns = make_columns()

        filter_t_in.on_change(
            "value",
            lambda _x, _y, _z: set_options(
                self.reset_options[my_id][1], self.reset_options[my_id][0]
            ),
        )

        def trigger_callback():
            cb = {}
            order = self.reset_options[my_id][1]
            for k, n in checkboxes:
                cb[n] = (k, [])
                for opt in order:
                    if opt in self.reset_options[my_id][0][n]:
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
            if len(sp) > 0:
                if sp[0] != "slick-cell":
                    y = int(sp[0]) - 1
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
                    self.reset_options[my_id][1] = move_element(
                        self.reset_options[my_id][1], y, True
                    )
                    set_options(
                        self.reset_options[my_id][1], self.reset_options[my_id][0]
                    )
                    trigger_callback()
                elif orderable and x == -2 and not y is None:
                    self.reset_options[my_id][1] = move_element(
                        self.reset_options[my_id][1], y, False
                    )
                    set_options(
                        self.reset_options[my_id][1], self.reset_options[my_id][0]
                    )
                    trigger_callback()
                elif x >= 0:
                    if y is None:
                        n = checkboxes[x][1]
                        bools = [
                            not name in self.reset_options[my_id][0][n]
                            for name in self.reset_options[my_id][1]
                            if matches_filter(filter_t_in, name.lower())
                        ]
                        if all(bools):
                            # nothing is activate -> set everything active
                            self.reset_options[my_id][0][n].extend([name for name in self.reset_options[my_id][
                                1
                            ] if matches_filter(filter_t_in, name.lower())])
                        else:  # none(bools) or some(bools)
                            # some things are active -> set everything inactive
                            self.reset_options[my_id][0][n] = [name for name in self.reset_options[my_id][0][n] if not matches_filter(filter_t_in, name.lower())]
                    else:
                        local_label = self.reset_options[my_id][1][y]
                        n = checkboxes[x][1]
                        if local_label in self.reset_options[my_id][0][n]:
                            self.reset_options[my_id][0][n].remove(local_label)
                        else:
                            self.reset_options[my_id][0][n].append(local_label)
                    set_options(
                        self.reset_options[my_id][1], self.reset_options[my_id][0]
                    )
                    trigger_callback()
            data_table.source.selected.update(indices=[])

        data_table.source.selected.on_change("indices", py_callback)
        data_table.source.selected.js_on_change("indices", js_callback)

        def on_change_rename(attr, old, new):
            return
            x, y = get_select()
            print("change", x, y)
            if not (x is None or y is None):
                if len(labels) > 1:
                    y += 1
                print("change", x, y, new["names"][y])
                # if orderable and x == -4:
                # r_opt = self.reset_options[my_id][1]
                # self.reset_options[my_id][1] = r_opt
                # print(new)
            data_table.source.selected.update(indices=[])

        data_table.source.on_change("data", on_change_rename)

        layout = column(
            [
                row(
                    [Div(text=title, width=SETTINGS_WIDTH - 210), filter_t_in],
                    sizing_mode="stretch_width",
                ),
                data_table,
            ],
            sizing_mode="stretch_width",
            css_classes=["outlnie_border", "tooltip", tooltip, "tooltip_fix_overlap"],
            margin=DIV_MARGIN,
        )

        def update():
            set_options(self.reset_options[my_id][1], self.reset_options[my_id][0])

        self.updatable_multi_choice[layout] = update

        return set_options, layout

    def multi_choice_auto(
        self,
        label,
        checkboxes,
        session_key,
        callback=None,
        orderable=True,
        renamable=False,
    ):
        set_options, layout = self.multi_choice(
            label,
            checkboxes,
            session_key,
            callback,
            orderable,
            renamable=renamable,
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
        if (
            factory_default["smoother_config_file_version"]
            > settings["smoother_config_file_version"]
        ):
            print(
                "INFO: Updating the",
                factory_default["display_name"],
                "config file. This is necessary because your smoother instalattion requires a newer config file version than the one you have (maybe you updated smoother?). This deletes your saved configuration.",
            )
            with open(out_file, "w") as f:
                json.dump(factory_default, f)

        with open(out_file, "r") as f:
            settings = json.load(f)

        if CONFIG_FILE_VERSION != settings["smoother_config_file_version"]:
            print(
                "WARNING: Config file version does not match: expected",
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
        apply_disabled = file_nr == self.session.get_value(["settings", "interface", "last_appplied_presetting"])
        apply_button = Button(
            label="",
            css_classes=SYM_CSS + ["fa_apply_disabled"] if apply_disabled else [ "fa_apply" ],
            width=SYM_WIDTH,
            height=SYM_WIDTH,
            sizing_mode="fixed",
            button_type="light",
            align="center",
            disabled=apply_disabled
        )
        self.apply_button_by_file_nr[str(file_nr)] = apply_button
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
                self.print("applying presetting " + str(file_nr))
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
            # @todo-low-prio why do i need to do this? the comp graph should realize that it needs to update...
            self.session.clear_cache()
            self.session.set_value(["settings", "interface", "last_appplied_presetting"], str(file_nr))
            self.trigger_render()
            if not bin.global_variables.quiet:
                self.print("applied")

        apply_button.on_click(lambda _: apply_event())

        if bin.global_variables.no_save:
            return row([name, apply_button, reset_button], sizing_mode="stretch_width")
        else:
            return row(
                [name, apply_button, save_button, reset_button],
                sizing_mode="stretch_width",
            )

    def make_slider_spinner(
        self,
        settings,
        width=200,
        on_change=None,
        spinner_width=80,
        sizing_mode="stretch_width",
        js_on_change=None,
        trigger_render=True,
    ):
        self.in_descriptions_json(settings)
        tooltip = "tooltip__" + "__".join(settings)
        title = self.get_button_name(settings)

        if on_change is None:

            def default_on_change(val):
                self.session.set_value(settings + ["val"], val)
                if trigger_render:
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
        if not js_on_change is None:
            slider.js_on_change("value_throttled", CustomJS(code=js_on_change))
            spinner.js_on_change("value_throttled", CustomJS(code=js_on_change))

        self.slider_spinner_config.append((slider, spinner, on_change, settings))

        return row(
            [slider, spinner],
            width=width,
            margin=DIV_MARGIN,
            css_classes=["tooltip", tooltip, "tooltip_fix_overlap"],
        )

    def make_range_slider_spinner(
        self,
        settings,
        width=200,
        on_change=None,
        spinner_width=80,
        sizing_mode="stretch_width",
    ):
        self.in_descriptions_json(settings)
        tooltip = "tooltip__" + "__".join(settings)
        title = self.get_button_name(settings)

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
            css_classes=["tooltip", tooltip, "tooltip_fix_overlap"],
        )

    def in_descriptions_json(self, key):
        d = self.description_json
        for k in key:
            if not k in d:
                print("WARNING:", key, "has no tooltip")
                return
            d = d[k]

    def get_button_name(self, key):
        d = self.button_names_json
        for k in key:
            if not k in d:
                print("WARNING:", key, "has no button name")
                return "???"
            d = d[k]
        return d

    def make_checkbox(
        self, settings=[], on_change=None, width=SETTINGS_WIDTH
    ):
        self.in_descriptions_json(settings)
        tooltip = "tooltip__" + "__".join(settings)
        title = self.get_button_name(settings)

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
            [div, cg], width=width, margin=DIV_MARGIN, css_classes=["tooltip", tooltip, "tooltip_fix_overlap"]
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
        self.v4c_col_expected = self.session.get_readable_range(
            self.session.get_value(["settings", "interface", "v4c", "col_from"]),
            self.session.get_value(["settings", "interface", "v4c", "col_to"]),
            True,
        )
        self.v4c_col.value = self.v4c_col_expected

        self.v4c_row_expected = self.session.get_readable_range(
            self.session.get_value(["settings", "interface", "v4c", "row_from"]),
            self.session.get_value(["settings", "interface", "v4c", "row_to"]),
            False,
        )
        self.v4c_row.value = self.v4c_row_expected
        self.trigger_render()

    def parse_v4c(self):
        change = False
        def interpret_error(s):
            self.error_interpret_pos += s + "\n"
        if self.v4c_col.value != self.v4c_col_expected:
            self.error_interpret_pos = ""
            col_start, col_end = self.session.interpret_range(self.v4c_col.value, True, report_error=interpret_error)
            change = True
            if not col_start is None:
                self.session.set_value(
                    ["settings", "interface", "v4c", "col_from"], col_start
                )
            if not col_end is None:
                self.session.set_value(
                    ["settings", "interface", "v4c", "col_to"], col_end
                )
            self.trigger_render()

        if self.v4c_row.value != self.v4c_row_expected:
            self.error_interpret_pos = ""
            row_start, row_end = self.session.interpret_range(self.v4c_row.value, False, report_error=interpret_error)
            change = True
            if not row_start is None:
                self.session.set_value(
                    ["settings", "interface", "v4c", "row_from"], row_start
                )
            if not row_end is None:
                self.session.set_value(
                    ["settings", "interface", "v4c", "row_to"], row_end
                )
            self.trigger_render()

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

        log_axis = self.session.get_value(["settings", "interface", "tracks_log_scale"])
        x_visible = len(self.raw_data_x.data["values"]) > 0
        self.raw_x.visible = self.show_hide["raw"] and x_visible and not log_axis
        self.raw_x_axis.visible = (
            self.show_hide["raw"]
            and x_visible
            and self.show_hide["axis"]
            and not log_axis
        )
        self.raw_x_log.visible = self.show_hide["raw"] and x_visible and log_axis
        self.raw_x_axis_log.visible = (
            self.show_hide["raw"] and x_visible and self.show_hide["axis"] and log_axis
        )
        y_visible = len(self.raw_data_y.data["values"]) > 0
        self.raw_y.visible = self.show_hide["raw"] and y_visible and not log_axis
        self.raw_y_axis.visible = (
            self.show_hide["raw"]
            and y_visible
            and self.show_hide["axis"]
            and not log_axis
        )
        self.raw_y_log.visible = self.show_hide["raw"] and y_visible and log_axis
        self.raw_y_axis_log.visible = (
            self.show_hide["raw"] and y_visible and self.show_hide["axis"] and log_axis
        )
        self.anno_x.visible = (
            len(self.anno_x_data.data["anno_name"]) > 0 and self.show_hide["annotation"]
        )
        self.anno_x_axis.visible = self.anno_x.visible and self.show_hide["axis"]
        self.anno_y.visible = (
            len(self.anno_y_data.data["anno_name"]) > 0 and self.show_hide["annotation"]
        )
        self.anno_y_axis.visible = self.anno_y.visible and self.show_hide["axis"]

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

        def set_norm_visibility(col, norm):
            c = [*col.children]
            col.children = []
            col.visible = (
                self.session.get_value(["settings", "normalization", "normalize_by"])
                == norm
            )
            col.children = c

        # set_norm_visibility(self.bin_test_norm, "radicl-seq")
        # set_norm_visibility(self.ice_norm, "ice")
        # set_norm_visibility(self.slices_norm, "grid-seq")
        self.chrom_layout_ploidy.visible = not self.session.get_value(
            ["settings", "normalization", "ploidy_coords"]
        )
        self.chrom_layout.visible = self.session.get_value(
            ["settings", "normalization", "ploidy_coords"]
        )

    def toggle_hide(self, key):
        self.show_hide[key] = not self.show_hide[key]
        self.update_visibility()

    def is_visible(self, key):
        return self.show_hide[key]

    def make_show_hide_menu(self):
        menu = []
        for name, key in self.names:
            menu.append((("☑ " if self.show_hide[key] else "☐ ") + name, key))
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
            if key not in self.show_hide:
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

        return self.show_hide_dropdown

    def config_show_hide(self, settings):
        for key in self.show_hide.keys():
            if key in settings:
                self.show_hide[key] = settings[key]
            else:
                self.show_hide[key] = True
        self.show_hide_dropdown.menu = self.make_show_hide_menu()
        self.update_visibility()

    def make_color_figure(self, palette):
        def hex_to_rgb(value):
            value = value.lstrip("#")
            lv = len(value)
            return [int(value[i : i + lv // 3], 16) for i in range(0, lv, lv // 3)]

        color_figure = figure(tools="", height=125, width=SETTINGS_WIDTH)
        color_figure.x(0, 0, color=None)
        scatter = color_figure.scatter(
            x="ranged_score",
            y=jitter("0", 1, distribution="normal"),
            line_color=None,
            color="color",
            source=self.heatmap_data,
        )
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
                        "(@bin_id_x{custom}, @bin_id_y{custom})",
                    ),
                    ("score", "@score_total"),
                    ("reads by group", "A: @score_a, B: @score_b"),
                ],
                formatters={
                    "@bin_id_x": CustomJSHover(
                        code=JS_HOVER, args={"source": self.custom_hover_x_data}
                    ),
                    "@bin_id_y": CustomJSHover(
                        code=JS_HOVER, args={"source": self.custom_hover_y_data}
                    ),
                },
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

    def set_area_range(self):
        self.area_range_expected = self.session.get_readable_area(
            int(math.floor(self.heatmap.x_range.start)),
            int(math.floor(self.heatmap.y_range.start)),
            int(math.ceil(self.heatmap.x_range.end)),
            int(math.ceil(self.heatmap.y_range.end)),
        )
        self.area_range.value = self.area_range_expected

    def parse_area_range(self):
        if self.area_range_expected != self.area_range.value:
            self.error_interpret_pos = ""
            def interpret_error(s):
                self.error_interpret_pos += s + "\n"
            i = self.session.interpret_area(
                self.area_range.value,
                self.heatmap.x_range.start,
                self.heatmap.y_range.start,
                self.heatmap.x_range.end,
                self.heatmap.y_range.end,
                report_error=interpret_error,
            )
            if not i[0] is None:
                self.heatmap.x_range.start = i[0]
            if not i[1] is None:
                self.heatmap.x_range.end = i[1]
            if not i[2] is None:
                self.heatmap.y_range.start = i[2]
            if not i[3] is None:
                self.heatmap.y_range.end = i[3]
            self.trigger_render()

    def save_tools(self, tools):
        if not self.session is None:
            self.session.set_value(["settings", "active_tools"], tools.split(";"))

    def make_panel(self, name, tooltip="", children=[]):
        self.curdoc.add_root(column(children, name=name))

    @gen.coroutine
    @without_document_lock
    def do_export(self):
        def unlocked_task():
            def callback():
                self.spinner.text = '<img id="spinner" src="biosmoother/static/stirring.gif" width="30px" height="30px">'

            self.curdoc.add_next_tick_callback(callback)
            export_to_server = self.session.get_value(
                ["settings", "export", "export_to_server"]
            )

            if self.session.get_value(["settings", "export", "export_format"]) == "tsv":
                if export_to_server:
                    export_tsv(self.session)
                else:
                    heatmap, track_x, track_y = get_tsv(self.session)
                    output_format = "text/tsv;charset=utf-8;"
                    output_data = [heatmap, track_x, track_y]
                    output_filename_extensions = [
                        ".heatmap.tsv",
                        ".track.x.tsv",
                        ".track.y.tsv",
                    ]
                    decode_to_bytes = False
            elif (
                self.session.get_value(["settings", "export", "export_format"]) == "svg"
            ):
                if export_to_server:
                    export_svg(self.session)
                else:
                    output_data = [get_svg(self.session)]
                    output_format = "image/svg+xml;charset=utf-8;"
                    output_filename_extensions = [".svg"]
                    decode_to_bytes = False
            elif (
                self.session.get_value(["settings", "export", "export_format"]) == "png"
            ):
                if export_to_server:
                    export_png(self.session)
                else:
                    output_data = [
                        base64.encodebytes(get_png(self.session)).decode("utf-8")
                    ]
                    output_format = "image/png"
                    output_filename_extensions = [".png"]
                    decode_to_bytes = True
            else:
                self.print("invalid value for export_format")

            def callback():
                if not export_to_server:
                    for data, ext in zip(output_data, output_filename_extensions):
                        self.download(
                            self.session.get_value(["settings", "export", "prefix"])
                            + ext,
                            data,
                            file_type=output_format,
                            decode_to_bytes=decode_to_bytes,
                        )
                self.spinner.text = '<img id="spinner" src="biosmoother/static/favicon.png" width="30px" height="30px">'
                s = "done exporting. Current Bin Size: " + self.get_readable_bin_size()
                self.print(s)
                self.print_status(s)

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
        self.log_div_text = ""
        if not self.session.can_save():
            self.print(
                "WARNING: cannot write to the index folder. Do you have write permissions in that directory? Enabling --no_save mode."
            )
            bin.global_variables.no_save = True
        if not os.path.exists(biosmoother_home_folder + "/conf/"):
            os.makedirs(biosmoother_home_folder + "/conf/")

        # create default file if none exists
        if not os.path.exists(biosmoother_home_folder + "/conf/default.json"):
            with open_default_json() as f_in:
                with open(biosmoother_home_folder + "/conf/default.json", "w") as f_out:
                    for l in f_in:
                        f_out.write(l)

        # replace default config if version is outdated
        with open_default_json() as f_in:
            version_in_default = json.load(f_in)["smoother_config_file_version"]
            with open(biosmoother_home_folder + "/conf/default.json", "r") as f_in_2:
                version_in_file = json.load(f_in_2)["smoother_config_file_version"]
        if version_in_default > version_in_file:
            print(
                "INFO: Updating the default config file. This is necessary because your smoother instalattion requires a newer config file version than the one you have (maybe you updated smoother?). This deletes your saved default configuration."
            )
            with open_default_json() as f_in:
                with open(biosmoother_home_folder + "/conf/default.json", "w") as f_out:
                    for l in f_in:
                        f_out.write(l)

        # load default file
        with open(biosmoother_home_folder + "/conf/default.json", "r") as f:
            self.settings_default = json.load(f)

        self.re_layout = None
        self.ping_div = None
        self.download_js_callback_div = None
        self.download_js_callback = None
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
        self.raw_x_log = None
        self.raw_x_axis_log = None
        self.raw_y_log = None
        self.raw_y_axis_log = None
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
            "idx_x": [],
            "ys": [],
            "idx_y": [],
            "colors": [],
            "anno_desc": [],
            "sample_id": [],
            "anno_idx": [],
        }
        self.ranked_data = ColumnDataSource(data=d)
        self.ranked_columns = None
        self.ranked_rows = None
        self.ranked_col_and_rows = None
        d = {"chr": [], "color": [], "xs": [], "ys": []}
        self.dist_dep_dec_plot_data = ColumnDataSource(data=d)
        self.dist_dep_dec_plot = None
        self.log_div = None
        self.v4c_col_expected = ""
        self.v4c_col = None
        self.v4c_row_expected = ""
        self.v4c_row = None
        d = {"chr": [], "index_left": [], "index_right": []}
        self.custom_hover_x_data = ColumnDataSource(data=d)
        self.custom_hover_y_data = ColumnDataSource(data=d)
        self.bin_test_norm = None
        self.ice_norm = None
        self.slices_norm = None
        self.chrom_layout = None
        self.chrom_layout_ploidy = None
        self.ploidy_file_in = None
        self.ploidy_last_uploaded_filename = None
        self.next_element_id = 0
        self.download_session = None
        self.error_interpret_pos = ""
        self.apply_button_by_file_nr = {}
        self.set_range_raw_x_axis = None
        self.set_range_raw_y_axis = None
        self.set_range_raw_x_axis_log = None
        self.set_range_raw_y_axis_log = None
        self.description_json = json.load(open_descriptions_json())
        self.button_names_json = json.load(open_button_names_json())

        self.do_layout()

    def do_layout(self):
        self.curdoc.clear()
        global SETTINGS_WIDTH
        tollbars = []
        self.heatmap = (
            FigureMaker()
            .name("heatmap")
            .range1d()
            .stretch()
            .combine_tools(tollbars)
            .get(self)
        )
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
                        "(@bin_id_x{custom}, @bin_id_y{custom})",
                    ),
                    ("score", "@score_total"),
                    ("reads by group", "A: @score_a, B: @score_b"),
                ],
                formatters={
                    "@bin_id_x": CustomJSHover(
                        code=JS_HOVER, args={"source": self.custom_hover_x_data}
                    ),
                    "@bin_id_y": CustomJSHover(
                        code=JS_HOVER, args={"source": self.custom_hover_y_data}
                    ),
                },
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

        # normal figures
        self.raw_x = (
            FigureMaker()
            .w(DEFAULT_SIZE)
            .link_y(self.heatmap)
            .hidden()
            .hide_on("raw", self)
            .combine_tools(tollbars)
            .get(self)
        )

        self.raw_x.add_tools(raw_hover_x)
        self.raw_x_axis = (
            FigureMaker().x_axis_of(self.raw_x, self).combine_tools(tollbars).get(self)
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
            .get(self)
        )
        self.raw_y.add_tools(raw_hover_y)
        self.raw_y_axis = (
            FigureMaker().y_axis_of(self.raw_y, self).combine_tools(tollbars).get(self)
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

        # log figures
        self.raw_x_log = (
            FigureMaker()
            .w(DEFAULT_SIZE)
            .link_y(self.heatmap)
            .hidden()
            .hide_on("raw", self)
            .combine_tools(tollbars)
            .log_x()
            .get(self)
        )

        self.raw_x_log.add_tools(raw_hover_x)
        self.raw_x_axis_log = (
            FigureMaker()
            .x_axis_of(self.raw_x_log, self)
            .log_x()
            .combine_tools(tollbars)
            .get(self)
        )
        self.raw_x_axis_log.xaxis.ticker = LogTicker(
            desired_num_ticks=3, num_minor_ticks=0
        )
        self.raw_x_log.xgrid.ticker = LogTicker(desired_num_ticks=3, num_minor_ticks=1)
        self.raw_x_log.xgrid.grid_line_alpha = 0
        self.raw_x_log.xgrid.minor_grid_line_alpha = 0.5
        self.raw_x_log.ygrid.minor_grid_line_alpha = 0.5

        self.raw_y_log = (
            FigureMaker()
            .h(DEFAULT_SIZE)
            .link_x(self.heatmap)
            .hidden()
            .hide_on("raw", self)
            .combine_tools(tollbars)
            .log_y()
            .get(self)
        )
        self.raw_y_log.add_tools(raw_hover_y)
        self.raw_y_axis_log = (
            FigureMaker()
            .y_axis_of(self.raw_y_log, self)
            .log_y()
            .combine_tools(tollbars)
            .get(self)
        )
        self.raw_y_axis_log.yaxis.ticker = LogTicker(
            desired_num_ticks=3, num_minor_ticks=0
        )
        self.raw_y_log.ygrid.ticker = LogTicker(desired_num_ticks=3, num_minor_ticks=1)
        self.raw_y_log.ygrid.grid_line_alpha = 0
        self.raw_y_log.ygrid.minor_grid_line_alpha = 0.5
        self.raw_y_log.xgrid.minor_grid_line_alpha = 0.5

        self.raw_x_log.multi_line(
            xs="values", ys="screen_pos", source=self.raw_data_x, line_color="colors"
        )  # , level="image"
        self.raw_y_log.multi_line(
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
            FigureMaker()
            .x_axis_of(self.anno_x, self)
            .combine_tools(tollbars)
            .name("anno_x_axis")
            .get(self)
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
            FigureMaker()
            .y_axis_of(self.anno_y, self)
            .combine_tools(tollbars)
            .name("anno_y_axis")
            .get(self)
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
            line_color="color",
            source=self.anno_x_data,
        )
        self.anno_y.hbar(
            y="anno_name",
            right="screen_end",
            left="screen_start",
            height="size",
            fill_color="color",
            line_color="color",
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
            x="idx_x", y="xs", color="colors", size=12, source=self.ranked_data
        )
        self.ranked_columns.xaxis.axis_label = "Samples ranked by RNA reads per kbp"
        self.ranked_columns.yaxis.axis_label = "RNA reads per kbp"
        self.ranked_columns.add_tools(ranked_hover)

        self.ranked_col_and_rows = figure(
            tools="pan,wheel_zoom,box_zoom,crosshair",
            y_axis_type="log",
            x_axis_type="log",
            height=200,
            width=SETTINGS_WIDTH,
        )
        tollbars.append(self.ranked_col_and_rows.toolbar)
        self.ranked_col_and_rows.dot(
            x="xs", y="ys", color="colors", size=12, source=self.ranked_data
        )
        self.ranked_col_and_rows.xaxis.axis_label = "RNA reads per kbp"
        self.ranked_col_and_rows.yaxis.axis_label = "Maximal DNA reads in bin"
        self.ranked_col_and_rows.add_tools(ranked_hover)

        self.ranked_rows = figure(
            tools="pan,wheel_zoom,box_zoom,crosshair",
            y_axis_type="log",
            height=200,
            width=SETTINGS_WIDTH,
        )
        self.ranked_rows.toolbar_location = None
        self.ranked_rows.dot(
            x="idx_y", y="ys", color="colors", size=12, source=self.ranked_data
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

        for p in [self.ranked_columns, self.ranked_rows, self.ranked_col_and_rows, self.dist_dep_dec_plot]:
            #p.sizing_mode = "stretch_width"
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
                        tick_label = numberWithCommas(tick / 1000000) + " Mbp";
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
        for fig in [self.anno_x, self.raw_x, self.raw_x_log, self.heatmap]:
            fig.add_tools(crosshair)
        crosshair = CrosshairTool(dimensions="height", line_color="lightgrey")
        for fig in [self.anno_y, self.raw_y, self.raw_y_log, self.heatmap]:
            fig.add_tools(crosshair)

        tool_bar = FigureMaker.get_tools(tollbars)
        show_hide = self.make_show_hide_dropdown(
            ["settings", "interface", "show_hide"],
            ("Secondary Axes", "axis"),
            ("Coordinates", "coords"),
            ("Regions", "regs"),
            (RAW_PLOT_NAME, "raw"),
            (ANNOTATION_PLOT_NAME, "annotation"),
            ("Sequence", "genome_sequence"),
        )

        in_group = self.dropdown_select(
            ("Sum [a+b+c+...]", "sum"),
            ("Minimium [min(a,b,c,...)]", "min"),
            ("Maximum [max(a,b,c,...)]", "max"),
            ("Difference [|a-b|+|a-c|+|b-c|+...]", "dif"),
            ("Mean [mean(a,b,c,...)]", "mean"),
            active_item=["settings", "replicates", "in_group"],
        )

        def betw_group_event(e):
            if self.session.get_value(["settings", "replicates", "between_group"]) == e:
                return
            if (
                self.session.get_value(["settings", "replicates", "between_group"])
                == "sub"
            ):
                self.session.set_value(
                    ["settings", "normalization", "color_range", "val_min"], 0
                )
                self.session.set_value(["settings", "normalization", "scale"], "max")
                self.session.set_value(["settings", "replicates", "between_group"], e)
                self.do_config()
            self.session.set_value(["settings", "replicates", "between_group"], e)
            if e == "sub":
                self.session.set_value(
                    ["settings", "normalization", "color_range", "val_min"], -1
                )
                self.session.set_value(["settings", "normalization", "scale"], "abs")
                self.do_config()
            self.trigger_render()

        betw_group = self.dropdown_select(
            ("Sum [a+b]", "sum"),
            ("Show First Group [a]", "1st"),
            ("Show Second Group [b]", "2nd"),
            ("Subtract [a-b]", "sub"),
            ("Difference [|a-b|]", "dif"),
            ("Divide [a/b if b!=0, 0 if b==0]", "div"),
            ("Divide [(a+0.000001) / (b+0.000001)]", "div+"),
            ("Minimum [min(a,b)]", "min"),
            ("Maximum [max(a,b)]", "max"),
            active_item=["settings", "replicates", "between_group"],
            event=betw_group_event,
        )

        symmetrie = self.dropdown_select(
            ("Show All Interactions", "all"),
            ("Only Show Symmetric Interactions", "sym"),
            ("Only Show Asymmetric Interactions", "asym"),
            ("Mirror Interactions to be Symmetric", "mirror"),
            active_item=["settings", "filters", "symmetry"],
        )

        last_bin_in_contig = self.dropdown_select(
            ("Merge remainder into last fullsized bin", "larger"),
            ("Hide remainder", "skip"),
            ("Display remainder", "smaller"),
            ("Make contig smaller", "fit_chrom_smaller"),
            ("Make contig larger", "fit_chrom_larger"),
            ("Extend remainder bin into next contig (only visual)", "cover_multiple"),
            active_item=["settings", "filters", "cut_off_bin"],
        )
        contig_smaller_than_bin = self.make_checkbox(
            settings=["settings", "filters", "show_contig_smaller_than_bin"],
        )

        norm_sele = [
            ("Reads per million", "rpm"),
            ("Reads per thousand", "rpk"),
            ("Binomial test", "radicl-seq"),
            ("Iterative Correction", "ice"),
            ("Associated slices", "grid-seq"),
            ("No normalization", "dont"),
        ]
        if Quarry.has_cooler_icing():
            norm_sele.append((("Cooler Iterative Correction", "cool-ice")))

        # normalization_cov = self.dropdown_select(
        #     ("Reads per million", "rpm"),
        #     ("Reads per thousand", "rpk"),
        #     ("Reads per million base pairs", "rpmb"),
        #     ("Reads per thousand base pairs", "rpkb"),
        #     ("No normalization", "dont"),
        #     active_item=["settings", "normalization", "normalize_by_coverage"],
        # )

        color_scale = self.dropdown_select(
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
            settings=["settings", "filters", "incomplete_alignments"],
        )

        ddd = self.make_checkbox(
            settings=["settings", "normalization", "ddd"],
        )
        ploidy_correct = self.make_checkbox(
            settings=["settings", "normalization", "ploidy_correct"],
        )
        ploidy_keep_distinct_group = self.make_checkbox(
            settings=["settings", "normalization", "ploidy_keep_distinct_group"],
        )
        ploidy_keep_inter_group = self.make_checkbox(
            settings=["settings", "normalization", "ploidy_keep_inter_group"],
        )
        ploidy_remove_others = self.make_checkbox(
            settings=["settings", "normalization", "ploidy_remove_others"],
        )
        ploidy_remove_intra_instance_contig = self.make_checkbox(
            settings=[
                "settings",
                "normalization",
                "ploidy_remove_intra_instance_contig",
            ],
        )

        def ploidy_coords_event(e):
            self.session.set_value(["settings", "normalization", "ploidy_coords"], e)
            self.update_visibility()
            self.trigger_render()

        ploidy_coords = self.make_checkbox(
            settings=["settings", "normalization", "ploidy_coords"],
            on_change=ploidy_coords_event,
        )
        ddd_show = self.make_checkbox(
            settings=["settings", "normalization", "ddd_show"],
        )
        ddd_ex_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "ddd_quantile"],
            sizing_mode="stretch_width",
        )
        ice_sparse_filter = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "ice_sparse_slice_filter"],
            sizing_mode="stretch_width",
        )
        ice_num_samples = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "num_ice_bins"],
            sizing_mode="stretch_width",
        )
        ice_mad_max = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "ice_mad_max"],
            sizing_mode="stretch_width",
        )
        ice_min_nz = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "ice_min_nz"],
            sizing_mode="stretch_width",
        )
        ice_ignore_n_diags = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "ice_ignore_n_diags"],
            sizing_mode="stretch_width",
        )
        ice_show_bias = self.make_checkbox(
            settings=["settings", "normalization", "ice_show_bias"],
        )
        ice_local = self.make_checkbox(
            settings=["settings", "normalization", "ice_local"],
        )
        ddd_sam_l = self.make_range_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "ddd_samples"],
            sizing_mode="stretch_width",
        )

        square_bins = self.make_checkbox(
            settings=["settings", "interface", "squared_bins"],
        )
        do_redraw = self.make_checkbox(
            settings=["settings", "interface", "do_redraw"],
        )
        render_now = Button(
            label="Render Now",
            width=SETTINGS_WIDTH,
            sizing_mode="fixed",
            css_classes=["other_button", "tooltip", "tooltip_render_now"],
            height=DROPDOWN_HEIGHT,
        )

        def render_now_event(x):
            self.force_render = True
            self.trigger_render()

        render_now.on_click(render_now_event)

        power_ten_bin = self.make_checkbox(
            settings=["settings", "interface", "snap_bin_size"],
        )

        color_picker = self.dropdown_select(
            ("Viridis", "Viridis256"),
            ("Plasma", "Plasma256"),
            ("Turbo", "Turbo256"),
            ("Fall", "Fall"),
            ("Low to High", "LowToHigh"),
            active_item=["settings", "interface", "color_palette"],
        )

        multi_mapping = self.dropdown_select(
            ("Count MMR if all mapping loci are within the same bin", "enclosed"),
            ("Count MMR if mapping loci minimum bounding-box overlaps bin", "overlaps"),
            ("Count MMR if bottom left mapping loci is within a bin", "first"),
            ("Count MMR if top right mapping loci is within a bin", "last"),
            ("Ignore MMRs", "points_only"),
            (
                "Count MMR if all mapping loci are within the same bin and ignore non-MMRs",
                "enclosed_only",
            ),
            (
                "Count MMR if mapping loci minimum bounding-box overlaps bin and ignore non-MMRs",
                "overlaps_only",
            ),
            active_item=["settings", "filters", "ambiguous_mapping"],
        )
        directionality = self.dropdown_select(
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

        default_label = self.session.get_value(["settings", "interface", "axis_lables"])
        self.heatmap_y_axis_2.yaxis.axis_label = default_label.split("_")[0]
        self.heatmap_x_axis_2.xaxis.axis_label = default_label.split("_")[1]

        axis_lables = self.dropdown_select(
            ("DNA / RNA", "DNA_RNA"),
            ("RNA / DNA", "RNA_DNA"),
            ("DNA / DNA", "DNA_DNA"),
            ("RNA / RNA", "RNA_RNA"),
            active_item=["settings", "interface", "axis_lables"],
            event=axis_labels_event,
        )

        def lower_bound_event(e):
            self.session.set_value(
                ["settings", "filters", "mapping_q", "val_min"], int(e)
            )
            self.trigger_render()

        ms_l = self.dropdown_select(
            (">= 0", "0"),
            *[
                (">= " + str(i), str(i))
                for i in range(255)
            ],
            active_item=["settings", "filters", "mapping_q", "val_min"],
            event=lower_bound_event,
        )

        def upper_bound_event(e):
            self.session.set_value(
                ["settings", "filters", "mapping_q", "val_max"], int(e)
            )
            self.trigger_render()

        ms_l_2 = self.dropdown_select(
            *[
                ("< " + str(i), str(i))
                for i in range(255)
            ],
            active_item=["settings", "filters", "mapping_q", "val_max"],
            event=upper_bound_event,
        )

        # ms_l = self.make_range_slider_spinner(
        #    width=SETTINGS_WIDTH,
        #    settings=["settings", "filters", "mapping_q"],
        #    sizing_mode="stretch_width",
        # )

        ibs_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "min_interactions"],
            sizing_mode="stretch_width",
        )

        crs_l = self.make_range_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "color_range"],
            sizing_mode="stretch_width",
        )

        self.ploidy_file_in = FileInput(
            # title="upload new ploidy file",
            disabled=bin.global_variables.no_save
        )

        self.ploidy_last_uploaded_filename = Div(text="No ploidy file has been uploaded yet.")
        if len(self.session.get_value(["settings", "normalization", "ploidy_last_uploaded_filename"])) > 0:
            self.ploidy_last_uploaded_filename.text = "Last uploaded ploidy file: " + self.session.get_value(["settings", "normalization", "ploidy_last_uploaded_filename"])

        def ploidy_file_name_change(a, o, n):
            self.ploidy_last_uploaded_filename.text = "Last uploaded ploidy file: " + n
            self.session.set_value(["settings", "normalization", "ploidy_last_uploaded_filename"], n)

        def ploidy_file_upload(a, o, n):
            self.session.set_ploidy_itr(b64decode(n).decode("utf-8").split("\n"), report_error=self.print)
            self.update_visibility()
            self.trigger_render()

        self.ploidy_file_in.on_change("filename", ploidy_file_name_change)
        self.ploidy_file_in.on_change("value", ploidy_file_upload)
        

        is_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "log_base"],
            sizing_mode="stretch_width",
        )

        def update_freq_event(val):
            self.session.set_value(["settings", "interface", "update_freq", "val"], val)

        ufs_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "interface", "update_freq"],
            on_change=update_freq_event,
            sizing_mode="stretch_width",
        )

        rs_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "interface", "zoom_redraw"],
            sizing_mode="stretch_width",
        )

        aas_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "interface", "add_draw_area"],
            sizing_mode="stretch_width",
        )

        dds_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "filters", "min_diag_dist"],
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
            settings=["settings", "interface", "anno_size"],
            sizing_mode="stretch_width",
            on_change=anno_size_slider_event,
        )

        def raw_size_slider_event(val):
            self.session.set_value(["settings", "interface", "raw_size", "val"], val)
            self.raw_x.width = val
            self.raw_x_axis.width = val
            self.raw_x_log.width = val
            self.raw_x_axis_log.width = val

            self.raw_y.height = val
            self.raw_y_axis.height = val
            self.raw_y_log.height = val
            self.raw_y_axis_log.height = val

        rss2_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "interface", "raw_size"],
            sizing_mode="stretch_width",
            on_change=raw_size_slider_event,
        )

        nb_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "interface", "max_num_bins"],
            sizing_mode="stretch_width",
        )

        rsa_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "p_accept"],
            sizing_mode="stretch_width",
        )
        bsmcq_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "grid_seq_max_bin_size"],
            sizing_mode="stretch_width",
        )
        grid_seq_samples_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "grid_seq_samples"],
            sizing_mode="stretch_width",
        )
        radicl_seq_samples_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "radicl_seq_samples"],
            sizing_mode="stretch_width",
        )
        export_coords_size = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "export", "coords"],
            sizing_mode="stretch_width",
            trigger_render=False,
        )
        axis_label_max_char = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "interface", "axis_label_max_char"],
            sizing_mode="stretch_width",
        )
        center_tracks_on_bins = self.make_checkbox(
            settings=["settings", "interface", "center_tracks_on_bins"],
        )
        zero_track_at_ends = self.make_checkbox(
            settings=["settings", "interface", "zero_track_at_ends"],
        )
        connect_tracks_over_contig_borders = self.make_checkbox(
            settings=["settings", "interface", "connect_tracks_over_contig_borders"],
        )

        def tracks_log_scale_change(active):
            self.session.set_value(
                ["settings", "interface", "tracks_log_scale"], active
            )
            self.update_visibility()

        tracks_log_scale = self.make_checkbox(
            settings=["settings", "interface", "tracks_log_scale"],
            on_change=tracks_log_scale_change,
        )
        export_contigs_size = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "export", "contigs"],
            sizing_mode="stretch_width",
            trigger_render=False,
        )
        export_axis_size = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "export", "axis"],
            sizing_mode="stretch_width",
            trigger_render=False,
        )
        export_stroke_width_secondary = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "export", "secondary_stroke_width"],
            sizing_mode="stretch_width",
            trigger_render=False,
        )
        grid_seq_display_background = self.make_checkbox(
            settings=["settings", "normalization", "grid_seq_display_background"],
        )
        radicl_seq_display_coverage = self.make_checkbox(
            settings=["settings", "normalization", "radicl_seq_display_coverage"],
        )
        grid_seq_column = self.make_checkbox(
            settings=["settings", "normalization", "grid_seq_axis_is_column"],
        )
        radicl_seq_column = self.make_checkbox(
            settings=["settings", "normalization", "radicl_seq_axis_is_column"],
        )
        grid_seq_intersection = self.make_checkbox(
            settings=["settings", "normalization", "grid_seq_filter_intersection"],
        )
        grid_seq_ignore_cis = self.make_checkbox(
            settings=["settings", "normalization", "grid_seq_ignore_cis"],
        )
        grid_seq_anno = self.dropdown_select_session(
            ["annotation", "filterable"],
            ["settings", "normalization", "grid_seq_annotation"],
        )
        grid_seq_rna_filter_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "grid_seq_rna_filter_v2"],
            sizing_mode="stretch_width",
        )
        grid_seq_dna_filter_l = self.make_slider_spinner(
            width=SETTINGS_WIDTH,
            settings=["settings", "normalization", "grid_seq_dna_filter_v2"],
            sizing_mode="stretch_width",
        )

        group_layout = self.multi_choice_auto(
            "Dataset Name",
            [
                [["replicates", "in_group_a"], "Pool A"],
                [["replicates", "in_group_b"], "Pool B"],
            ],
            ["replicates", "list"],
            orderable=False,
        )

        annos_layout = self.multi_choice_auto(
            "Annotation Name",
            [
                [["annotation", "visible_x"], "Column"],
                [["annotation", "visible_y"], "Row"],
            ],
            ["annotation", "list"],
        )

        power_tick = FuncTickFormatter(
            code="""
            if (tick / 9 >= 9)
                return Math.ceil((1 + tick % 9)) + "*10^" + Math.floor(tick / 9) + "bp";
            else if (tick / 9 >= 6)
                return Math.ceil((1 + tick % 9) * Math.pow(10, Math.floor(tick / 9)-6)) + "Mbp";
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
            css_classes=["tooltip", "tooltip__settings__interface__min_bin_size"],
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

        def callback_bin_size(a):
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
        button_s_up.on_click(lambda _: callback_bin_size(1))
        button_s_down = Button(
            label="",
            css_classes=["other_button", "fa_sort_down_solid"],
            button_type="light",
            width=10,
            height=10,
        )
        button_s_down.on_click(lambda _: callback_bin_size(-1))

        mmbs_l = row(
            [self.min_max_bin_size, column([button_s_up, button_s_down])],
            margin=DIV_MARGIN,
            width=SETTINGS_WIDTH,
        )

        self.info_status_bar = Div(
            text="Loading index.", sizing_mode="stretch_width"
        )
        self.info_status_bar.height = 26
        self.info_status_bar.min_height = 26
        self.info_status_bar.max_height = 26
        self.info_status_bar.height_policy = "fixed"

        status_bar_row = row(
            [self.info_status_bar],
            sizing_mode="stretch_width",
            css_classes=["top_border"],
            name="status_bar",
        )

        self.spinner = Div(
            text='<img src="biosmoother/static/favicon.png" width="30px" height="30px">'
        )

        norm_layout = self.multi_choice_auto(
            "Dataset name",
            [
                [["coverage", "in_column"], "Column"],
                [["coverage", "in_row"], "Row"],
            ],
            ["coverage", "list"],
            orderable=False,
        )

        def anno_coords_event(e):
            if self.session.get_value(["contigs", "annotation_coordinates"]) == e:
                return

            self.session.set_value(["contigs", "annotation_coordinates"], e)
            can_combine = self.session.get_value(
                ["contigs", "annotation_coordinates"]
            ) in self.session.get_value(["annotation", "filterable"])

            if (
                can_combine
                and self.session.get_value(
                    ["settings", "filters", "multiple_annos_in_bin"]
                )
                != "combine"
            ):
                self.session.set_value(
                    ["settings", "filters", "multiple_annos_in_bin"], "combine"
                )
                self.do_config()
            if (
                not can_combine
                and self.session.get_value(
                    ["settings", "filters", "multiple_annos_in_bin"]
                )
                == "combine"
            ):
                self.session.set_value(
                    ["settings", "filters", "multiple_annos_in_bin"], "max_fac_pow_two"
                )
                self.do_config()
            self.trigger_render()

        anno_coords = self.dropdown_select_session(
            ["annotation", "list"],
            ["contigs", "annotation_coordinates"],
            event=anno_coords_event,
        )
        coords_x = self.make_checkbox(
            settings=["settings", "filters", "anno_coords_col"],
        )
        coords_y = self.make_checkbox(
            settings=["settings", "filters", "anno_coords_row"],
        )

        anno_read_filter_present = self.multi_choice_auto(
            "Annotation Name",
            [
                [["annotation", "filter_present_x"], "Column"],
                [["annotation", "filter_present_y"], "Row"],
            ],
            ["annotation", "filterable"],
            orderable=False,
        )
        anno_read_filter_absent = self.multi_choice_auto(
            "Annotation Name",
            [
                [["annotation", "filter_absent_x"], "Column"],
                [["annotation", "filter_absent_y"], "Row"],
            ],
            ["annotation", "filterable"],
            orderable=False,
        )

        self.chrom_layout = self.multi_choice_auto(
            "Contig Name",
            [
                [["contigs", "displayed_on_x"], "Column"],
                [["contigs", "displayed_on_y"], "Row"],
            ],
            ["contigs", "list"],
        )
        self.chrom_layout_ploidy = self.multi_choice_auto(
            "Contig Name",
            [
                [["contigs", "displayed_on_x_ploidy"], "Column"],
                [["contigs", "displayed_on_y_ploidy"], "Row"],
            ],
            ["contigs", "ploidy_list"],
        )

        multiple_anno_per_bin = self.dropdown_select(
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
            ("Stretch one bin over entire annotation", "stretch"),
            ("Show several bins for the annotation", "separate"),
            ("Make all annotations size 1", "squeeze"),
            active_item=["settings", "filters", "anno_in_multiple_bins"],
        )

        export_button = Button(
            label="Export",
            width=SETTINGS_WIDTH - 37,
            sizing_mode="fixed",
            css_classes=["other_button", "tooltip", "tooltip_export"],
            height=DROPDOWN_HEIGHT,
        )

        def exp_event(x):
            self.do_export()

        export_button.on_click(exp_event)

        export_format = self.dropdown_select(
            ("TSV-file", "tsv"),
            ("SVG-picture", "svg"),
            ("PNG-picture", "png"),
            active_item=["settings", "export", "export_format"],
            trigger_render=False,
        )

        export_full = self.make_checkbox(
            settings=["settings", "export", "do_export_full"],
        )

        export_to_server = self.make_checkbox(
            settings=["settings", "export", "export_to_server"],
        )

        export_label = Div(
            text="Output Prefix:", css_classes=["tooltip", "tooltip__settings__export__prefix"]
        )
        export_label.margin = DIV_MARGIN
        self.export_file = TextInput(
            css_classes=["tooltip", "tooltip__settings__export__prefix"],
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
            css_classes=["tooltip", "tooltip__settings__interface__color_low"],
            height=DEFAULT_TEXT_INPUT_HEIGHT * 2,
        )
        self.high_color = ColorPicker(
            title="Color High",
            css_classes=["tooltip", "tooltip__settings__interface__color_high"],
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
            text="Index path:" + os.environ["biosmoother_index_path"]
            if "biosmoother_index_path" in os.environ
            else "unknown"
        )
        self.download_session = Button(
            label="Download current session",
            width=SETTINGS_WIDTH,
            sizing_mode="fixed",
            css_classes=[
                "other_button",
                "tooltip",
                "tooltip_download_session",
            ],
            height=DROPDOWN_HEIGHT,
        )

        def callback(e):
            self.download(
                "session.json",
                json.dumps(self.session.get_session()),
                "test/json;charset=utf-8;",
            )

        self.download_session.on_click(callback)

        upload_session = FileInput(
            disabled=bin.global_variables.no_save
        )
        
        def session_upload(a, o, n):
            self.session.set_session(json.loads(b64decode(n).decode("utf-8")))
            self.session.establish_backwards_compatibility()
            self.heatmap.x_range.start = self.session.get_value(["area", "x_start"])
            self.heatmap.x_range.end = self.session.get_value(["area", "x_end"])
            self.heatmap.y_range.start = self.session.get_value(["area", "y_start"])
            self.heatmap.y_range.end = self.session.get_value(["area", "y_end"])
            self.update_visibility()
            self.trigger_render()

        upload_session.on_change("value", session_upload)

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
                if os.path.exists(
                    os.environ["biosmoother_index_path"] + ".biosmoother_index/"
                ):
                    path = os.environ["biosmoother_index_path"] + ".biosmoother_index/"
            if not path is None:
                with open(path + "/default_session.json", "r") as f:
                    default_session = json.load(f)
                    default_session["settings"] = self.settings_default
            self.session.set_session(default_session)
            self.session.establish_backwards_compatibility()
            self.do_config()
            self.trigger_render()

        reset_session.on_click(reset_event)

        self.ticker_x = ExtraTicksTicker(extra_ticks=[])  # pyright: ignore type
        self.ticker_x_2 = IntermediateTicksTicker(  # pyright: ignore missing import
            extra_ticks=[]
        )  # pyright: ignore type
        self.ticker_y = ExtraTicksTicker(extra_ticks=[])  # pyright: ignore type
        self.ticker_y_2 = IntermediateTicksTicker(  # pyright: ignore missing import
            extra_ticks=[]
        )  # pyright: ignore type

        def get_formatter_tick():
            return FuncTickFormatter(
                args={
                    "screen_starts": [],
                    "index_starts": [],
                    "genome_end": 0,
                    "dividend": 1,
                },
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
                                tick_label = numberWithCommas(tick_pos / 1000000) + " Mbp";
                            else if (tick_pos % 1000 == 0)
                                tick_label = numberWithCommas(tick_pos / 1000) + " kbp";
                            else
                                tick_label = numberWithCommas(tick_pos) + " bp";
                            return tick_label;
                        """,
            )

        def get_formatter_chr():
            return FuncTickFormatter(
                args={"contig_starts": [], "genome_end": 0, "contig_names": []},
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
            css_classes=SYM_CSS + ["fa_page_previous_solid", "tooltip", "tooltip_undo", "tooltip_fix_overlap"],
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
            css_classes=SYM_CSS + ["fa_page_next_solid", "tooltip", "tooltip_redo", "tooltip_fix_overlap"],
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
        self.heatmap_x_axis_2.xaxis.major_tick_line_color = None
        self.heatmap_x_axis_2.xaxis.major_tick_out = 0
        self.heatmap_x_axis_2.y_range.start = 1
        self.heatmap_x_axis_2.y_range.end = 2
        self.heatmap_x_axis_2.background_fill_color = None
        self.heatmap_x_axis_2.outline_line_color = None
        self.heatmap_x_axis_2.ygrid.grid_line_alpha = 0.0

        self.heatmap_x_axis_3.xaxis.ticker = self.ticker_x
        self.heatmap_x_axis_3.xaxis.major_label_text_font_size = "0pt"
        self.heatmap_x_axis_3.xaxis.formatter = FuncTickFormatter(code='return "";')
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
        self.heatmap_y_axis_3.yaxis.major_label_text_font_size = "0pt"
        self.heatmap_y_axis_3.yaxis.formatter = FuncTickFormatter(code='return "";')
        self.heatmap_y_axis_3.yaxis.minor_tick_line_color = None
        self.heatmap_y_axis_3.x_range.start = 1
        self.heatmap_y_axis_3.x_range.end = 2
        self.heatmap_y_axis_3.background_fill_color = None
        self.heatmap_y_axis_3.outline_line_color = None
        self.heatmap_y_axis_3.xgrid.grid_line_alpha = 0.0

        for plot in [
            self.heatmap,
            self.raw_x,
            self.raw_x_log,
            self.anno_x,
            self.raw_y,
            self.raw_y_log,
            self.anno_y,
            self.heatmap_x_axis,
            self.heatmap_y_axis,
            self.anno_x_axis,
            self.anno_y_axis,
            self.heatmap_x_axis_2,
            self.heatmap_y_axis_2,
            self.heatmap_x_axis_3,
            self.heatmap_y_axis_3,
            self.raw_x_axis,
            self.raw_y_axis,
            self.raw_x_axis_log,
            self.raw_y_axis_log,
        ]:
            plot.js_on_change("visible", CustomJS(code=JS_UPDATE_LAYOUT))
            plot.js_on_change("outer_height", CustomJS(code=JS_UPDATE_LAYOUT))
            plot.js_on_change("outer_height", CustomJS(code=JS_UPDATE_LAYOUT))

        for plot in [self.anno_y_axis, self.raw_y_axis]:
            plot.align = "end"

        for plot in [
            self.heatmap,
            self.raw_y,
            self.raw_y_log,
            self.anno_y,
            self.heatmap_x_axis,
        ]:
            plot.xgrid.ticker = self.ticker_x
            plot.xaxis.major_label_text_align = "left"
            plot.xaxis.ticker.min_interval = 1
        for plot in [
            self.heatmap,
            self.raw_x,
            self.raw_x_log,
            self.anno_x,
            self.heatmap_y_axis,
        ]:
            plot.ygrid.ticker = self.ticker_y
            plot.yaxis.major_label_text_align = "right"
            plot.yaxis.ticker.min_interval = 1

        log_div = Div(text="Log:", sizing_mode="stretch_width")
        self.log_div = Div(
            css_classes=["scroll_y2", "white_background"],
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
                export_label,
                self.export_file,
                export_format,
                export_full,
                export_coords_size,
                export_contigs_size,
                export_axis_size,
                export_stroke_width_secondary,
                row([self.spinner, export_button]),
            ]
            self.session.set_value(["settings", "export", "export_to_server"], False)
        else:
            export_panel = [
                export_label,
                self.export_file,
                export_format,
                export_full,
                export_to_server,
                export_coords_size,
                export_contigs_size,
                export_axis_size,
                export_stroke_width_secondary,
                row([self.spinner, export_button]),
            ]

        v4c_norm_viewpoint_size = self.make_checkbox(
            settings=["settings", "interface", "v4c", "norm_by_viewpoint_size"],
        )

        do_v4c_col = self.make_checkbox(
            settings=["settings", "interface", "v4c", "do_col"],
        )

        v4c_col_label = Div(
            text="Column Viewpoint", css_classes=["tooltip", "tooltip__settings__interface__v4c__col"]
        )
        v4c_col_label.margin = DIV_MARGIN
        self.v4c_col = TextInput(
            css_classes=["tooltip", "tooltip__settings__interface__v4c__col"],
            height=DEFAULT_TEXT_INPUT_HEIGHT,
            width=SETTINGS_WIDTH,
        )
        self.v4c_col.on_change("value", lambda x, y, z: self.parse_v4c())

        do_v4c_row = self.make_checkbox(
            settings=["settings", "interface", "v4c", "do_row"],
        )
        v4c_row_label = Div(
            text="Row Viewpoint", css_classes=["tooltip", "tooltip__settings__interface__v4c__row"]
        )
        v4c_row_label.margin = DIV_MARGIN
        self.v4c_row = TextInput(
            css_classes=["tooltip", "tooltip__settings__interface__v4c__row"],
            height=DEFAULT_TEXT_INPUT_HEIGHT,
            width=SETTINGS_WIDTH,
        )
        self.v4c_row.on_change("value", lambda x, y, z: self.parse_v4c())

        # self.curdoc.add_root(column([normalization, normalization_cov], name="norm_by"))

        self.make_panel("presetting", "", [*quick_configs])
        self.make_panel("export", "", export_panel)
        self.make_panel(
            "info",
            "",
            [version_info, index_info, self.download_session, 
                Div(text="upload session:"), upload_session, log_div, self.log_div],
        )

        def norm_event(e):
            self.session.set_value(["settings", "normalization", "normalize_by"], e)
            self.update_visibility()
            self.trigger_render()

        normalization = self.dropdown_select(
            *norm_sele,
            active_item=["settings", "normalization", "normalize_by"],
            event=norm_event,
        )

        self.make_panel(
            "mainNorm",
            "",
            [
                normalization,
            ],
        )
        self.make_panel(
            "binom",
            "",
            [
                rsa_l,
                radicl_seq_display_coverage,
                radicl_seq_column,
                radicl_seq_samples_l,
            ],
        )
        self.make_panel(
            "ic",
            "",
            [
                ice_sparse_filter,
                ice_num_samples,
                ice_show_bias,
                ice_local,
                ice_mad_max,
                ice_min_nz,
                ice_ignore_n_diags,
            ],
        )
        self.make_panel(
            "assoc",
            "",
            [
                grid_seq_samples_l,
                bsmcq_l,
                grid_seq_column,
                grid_seq_anno,
                grid_seq_display_background,
                grid_seq_intersection,
                grid_seq_ignore_cis,
                grid_seq_rna_filter_l,
                self.ranked_columns,
                grid_seq_dna_filter_l,
                self.ranked_rows,
                self.ranked_col_and_rows,
            ],
        )
        self.make_panel(
            "ploidy",
            "",
            [
                ploidy_correct,
                ploidy_coords,
                ploidy_remove_intra_instance_contig,
                ploidy_keep_inter_group,
                ploidy_keep_distinct_group,
                ploidy_remove_others,
                Div(text="replace ploidy file:"),
                self.ploidy_file_in,
                self.ploidy_last_uploaded_filename,
            ],
        )
        self.make_panel(
            "ddd",
            "",
            [
                ddd,
                ddd_show,
                ddd_sam_l,
                ddd_ex_l,
                self.dist_dep_dec_plot,
            ],
        )
        self.make_panel(
            "datapools",
            "",
            [
                in_group,
                betw_group,
                group_layout,
                ibs_l,
                norm_layout,
            ],
        )
        self.make_panel(
            "mapping",
            "",
            [
                ms_l,
                ms_l_2,
                incomp_align_layout,
                multi_mapping,
                directionality,
            ],
        )
        self.make_panel(
            "coordinates",
            "",
            [
                self.chrom_layout,
                self.chrom_layout_ploidy,
                symmetrie,
                dds_l,
                anno_coords,
                coords_x,
                coords_y,
                multiple_bin_per_anno,
                multiple_anno_per_bin,
            ],
        )
        self.make_panel(
            "annotation",
            "",
            [
                annos_layout,
                anno_read_filter_present,
                anno_read_filter_absent,
            ],
        )
        self.make_panel(
            "color",
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
        )
        self.make_panel(
            "panels",
            "",
            [
                show_hide,
                ass_l,
                rss2_l,
                axis_lables,
                axis_label_max_char,
                center_tracks_on_bins,
                zero_track_at_ends,
                connect_tracks_over_contig_borders,
                tracks_log_scale,
            ],
        )
        self.make_panel(
            "bins",
            "",
            [
                nb_l,
                mmbs_l,
                square_bins,
                power_ten_bin,
                last_bin_in_contig,
                contig_smaller_than_bin,
            ],
        )
        self.make_panel(
            "virtual4c",
            "",
            [
                do_v4c_col,
                v4c_col_label,
                self.v4c_col,
                do_v4c_row,
                v4c_row_label,
                self.v4c_row,
                v4c_norm_viewpoint_size,
            ],
        )
        self.make_panel(
            "rendering",
            "",
            [ufs_l, rs_l, aas_l, do_redraw, render_now],
        )

        quit_ti = TextInput(value="keepalive", name="quit_ti", visible=False)

        def close_server(x, y, z):
            if bin.global_variables.keep_alive:
                if not bin.global_variables.quiet:
                    print("session exited; keeping server alive")
            else:
                if not bin.global_variables.quiet:
                    print("closing server since session exited")
                if not bin.global_variables.no_save:
                    try:
                        self.session.save_session()
                    except:
                        self.print(
                            "WARNING: could not save session. Do you have write permissions for the index?"
                        )
                sys.exit()

        quit_ti.on_change("value", close_server)
        self.re_layout = Div(text="")
        self.re_layout.js_on_change("text", CustomJS(code=JS_UPDATE_LAYOUT))
        self.download_js_callback = CustomJS(
            code=JS_DOWNLOAD,
            args={
                "filename": "unknown",
                "filetext": "unknown",
                "filetype": "text/csv;charset=utf-8;",
                "decode_to_bytes": False,
            },
        )
        self.download_js_callback_div = Div(text="")
        self.download_js_callback_div.js_on_change("text", self.download_js_callback)

        communication = row(
            [quit_ti, self.re_layout, self.download_js_callback_div],
            name="communication",
        )
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
        self.curdoc.add_root(column([self.raw_x, self.raw_x_log], name="raw_x"))
        self.curdoc.add_root(
            row(
                [self.raw_x_axis, self.raw_x_axis_log],
                name="raw_x_axis",
                sizing_mode="stretch_height",
            )
        )
        self.curdoc.add_root(self.anno_y)
        self.curdoc.add_root(self.anno_y_axis)
        self.curdoc.add_root(row([self.raw_y, self.raw_y_log], name="raw_y"))
        self.curdoc.add_root(
            column(
                [self.raw_y_axis, self.raw_y_axis_log],
                name="raw_y_axis",
                sizing_mode="stretch_width",
            )
        )
        self.curdoc.add_root(communication)
        self.curdoc.add_root(status_bar_row)
        self.curdoc.add_root(tools_bar)

        self.update_visibility()

    def download(
        self,
        filename,
        file_data,
        file_type="text/tsv;charset=utf-8;",
        decode_to_bytes=False,
    ):
        # other file_types: image/svg+xml;
        # other file_types: image/png;
        self.download_js_callback.args["filename"] = filename
        self.download_js_callback.args["filetext"] = file_data
        self.download_js_callback.args["filetype"] = file_type
        self.download_js_callback.args["decode_to_bytes"] = decode_to_bytes
        self.download_js_callback_div.text = (
            "blub" if self.download_js_callback_div.text == "" else ""
        )

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

    def print(self, s, font_color=None):
        s = datetime.now().strftime("[%H:%M:%S] ") + s
        if not bin.global_variables.quiet:
            print(s)
        self.log_div_text += ("" if font_color is None else "<font color=" + font_color + ">") + \
                             s.replace("\n", "<br>") + ("" if font_color is None else "</font>") + "<br>"
        # self.log_div_text = self.log_div_text[-5000:]

    def update_log_div(self):
        def callback():
            self.log_div.text = self.log_div_text

        self.curdoc.add_next_tick_callback(callback)

    def print_status(self, s):
        def callback():
            self.info_status_bar.text = s.replace("\n", " | ")

        self.curdoc.add_next_tick_callback(callback)

    def get_readable_bin_size(self):
        w_bin, h_bin = self.session.get_bin_size(self.print)

        def readable_display(l):
            def add_commas(x):
                return "{:,}".format(x)

            if l % 1000000 == 0:
                return str(add_commas(l // 1000000)) + "Mbp"
            elif l % 1000 == 0:
                return str(add_commas(l // 1000)) + "kbp"
            else:
                return str(add_commas(l)) + "bp"

        if w_bin == h_bin:
            return readable_display(w_bin)
        return readable_display(w_bin) + " x " + readable_display(h_bin)

    @gen.coroutine
    @without_document_lock
    def render(self, zoom_in_render):
        def unlocked_task():
            def cancelable_task():
                def callback():
                    self.spinner.text = '<img id="spinner" src="biosmoother/static/stirring.gif" width="30px" height="30px">'

                self.curdoc.add_next_tick_callback(callback)

                start_time = time.perf_counter()

                self.session.update_cds(self.print)

                d_heatmap = self.session.get_heatmap(self.print)

                raw_data_x = self.session.get_tracks(False, self.print)
                raw_data_y = self.session.get_tracks(True, self.print)
                min_max_tracks_x = self.session.get_min_max_tracks(False, self.print)
                min_max_tracks_y = self.session.get_min_max_tracks(True, self.print)
                min_max_tracks_non_zero_x = self.session.get_min_max_tracks_non_zero(
                    False, self.print
                )
                min_max_tracks_non_zero_y = self.session.get_min_max_tracks_non_zero(
                    True, self.print
                )

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
                bin_coords_x = self.session.get_bin_coords_cds(True, self.print)
                bin_coords_y = self.session.get_bin_coords_cds(False, self.print)

                palette = self.session.get_palette(self.print)

                ranked_slices = self.session.get_ranked_slices(self.print)
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
                if len(error) > 0 and len(self.error_interpret_pos) > 0:
                    error += "\n"
                error += self.error_interpret_pos
                self.error_interpret_pos = ""
                self.have_error = len(error) > 0
                error_text = (
                    "No errors"
                    if len(error) == 0
                    else "ERRORS:\n" + error
                )
                error_text_status = (
                    "None"
                    if len(error) == 0
                    else '<font color="#FF0000">' + error.split("\n")[0][:100] + ("..." if len(error.split("\n")[0]) > 100 else "") + ' (<u onclick="openTab(\'File\', \'main\'); openTab(\'Info\', \'file\')">see error log in File->Info</u>)</font>'
                )
                end_time = time.perf_counter()
                start_render_time = time.perf_counter()

                @gen.coroutine
                def callback():
                    self.curdoc.hold()
                    if not bin.global_variables.quiet:
                        self.print(error_text, font_color="#FF0000" if self.have_error else None)
                    self.color_layout.children = [self.make_color_figure(palette)]

                    file_nr = self.session.get_value(["settings", "interface", "last_appplied_presetting"])
                    for file_nr_curr, apply_button_curr in self.apply_button_by_file_nr.items():
                        apply_button_curr.css_classes = ["other_button"] + (["fa_apply_disabled"] if file_nr_curr == file_nr else [ "fa_apply" ])
                        apply_button_curr.disabled = file_nr_curr == file_nr

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

                    RANGE_PADDING = 0.1
                    LOG_PADDING = 0.5
                    min_max_tracks_x_log = (
                        min_max_tracks_non_zero_x[0] * LOG_PADDING,
                        min_max_tracks_non_zero_x[1] / LOG_PADDING,
                    )
                    range_padding_x = RANGE_PADDING * (
                        min_max_tracks_x[1] - min_max_tracks_x[0]
                    )
                    min_max_tracks_x[0] -= range_padding_x
                    min_max_tracks_x[1] += range_padding_x
                    
                    min_max_tracks_y_log = (
                        min_max_tracks_non_zero_y[0] * LOG_PADDING,
                        min_max_tracks_non_zero_y[1] / LOG_PADDING,
                    )
                    range_padding_y = RANGE_PADDING * (
                        min_max_tracks_y[1] - min_max_tracks_y[0]
                    )
                    min_max_tracks_y[0] -= range_padding_y
                    min_max_tracks_y[1] += range_padding_y

                    if math.isfinite(min_max_tracks_x[0]) and math.isfinite(min_max_tracks_x[1]):
                        if self.set_range_raw_x_axis != min_max_tracks_x:
                            self.raw_x_axis.x_range.start = min_max_tracks_x[0]
                            self.raw_x_axis.x_range.end = min_max_tracks_x[1]
                            self.set_range_raw_x_axis = min_max_tracks_x

                    if math.isfinite(min_max_tracks_y[0]) and math.isfinite(min_max_tracks_y[1]):
                        if self.set_range_raw_y_axis != tuple(min_max_tracks_y):
                            self.raw_y_axis.y_range.start = min_max_tracks_y[0]
                            self.raw_y_axis.y_range.end = min_max_tracks_y[1]
                            self.set_range_raw_y_axis = tuple(min_max_tracks_y)


                    if math.isfinite(min_max_tracks_x_log[0]) and math.isfinite(min_max_tracks_x_log[1]):
                        if self.set_range_raw_x_axis_log != tuple(min_max_tracks_x_log):
                            self.raw_x_axis_log.x_range.start = min_max_tracks_x_log[0]
                            self.raw_x_axis_log.x_range.end = min_max_tracks_x_log[1]
                            self.set_range_raw_x_axis_log = tuple(min_max_tracks_x_log)

                    if math.isfinite(min_max_tracks_y_log[0]) and math.isfinite(min_max_tracks_y_log[1]):
                        if self.set_range_raw_y_axis_log != tuple(min_max_tracks_y_log):
                            self.raw_y_axis_log.y_range.start = min_max_tracks_y_log[0]
                            self.raw_y_axis_log.y_range.end = min_max_tracks_y_log[1]
                            self.set_range_raw_y_axis_log = tuple(min_max_tracks_y_log)

                    def set_bounds_x(
                        plot, color=None
                    ):
                        ra = self.plot_render_area(plot)
                        ra.bottom = render_area[1]
                        ra.top = render_area[3]
                        if not color is None:
                            ra.fill_color = color
                    def set_bounds_y(
                        plot, color=None
                    ):
                        ra = self.plot_render_area(plot)
                        ra.left = render_area[0]
                        ra.right = render_area[2]
                        if not color is None:
                            ra.fill_color = color

                    set_bounds_x(self.raw_x)
                    set_bounds_x(self.raw_x_log)
                    set_bounds_y(self.raw_y)
                    set_bounds_y(self.raw_y_log)
                    set_bounds_x(self.anno_x)
                    set_bounds_y(self.anno_y)

                    set_bounds_x(self.heatmap, color=b_col)
                    set_bounds_y(self.heatmap, color=b_col)

                    self.heatmap_data.data = d_heatmap
                    self.raw_data_x.data = raw_data_x
                    log_axis = self.session.get_value(
                        ["settings", "interface", "tracks_log_scale"]
                    )
                    x_visible = len(raw_data_x["values"]) > 0
                    self.raw_x.visible = (
                        self.show_hide["raw"] and x_visible and not log_axis
                    )
                    self.raw_x_axis.visible = (
                        self.show_hide["raw"] and x_visible and not log_axis
                    )
                    self.raw_x_log.visible = (
                        self.show_hide["raw"] and x_visible and log_axis
                    )
                    self.raw_x_axis_log.visible = (
                        self.show_hide["raw"] and x_visible and log_axis
                    )
                    self.raw_data_y.data = raw_data_y
                    y_visible = len(raw_data_y["values"]) > 0
                    self.raw_y.visible = (
                        self.show_hide["raw"] and y_visible and not log_axis
                    )
                    self.raw_y_axis.visible = (
                        self.show_hide["raw"] and y_visible and not log_axis
                    )
                    self.raw_y_log.visible = (
                        self.show_hide["raw"] and y_visible and log_axis
                    )
                    self.raw_y_axis_log.visible = (
                        self.show_hide["raw"] and y_visible and log_axis
                    )

                    self.anno_x.x_range.factors = displayed_annos_x
                    self.anno_y.y_range.factors = displayed_annos_y[::-1]

                    self.anno_x_data.data = d_anno_x
                    self.anno_y_data.data = d_anno_y
                    self.anno_x.visible = (
                        len(d_anno_x["anno_name"]) > 0 and self.show_hide["annotation"]
                    )
                    self.anno_x_axis.visible = self.anno_x.visible
                    self.anno_y.visible = (
                        len(d_anno_y["anno_name"]) > 0 and self.show_hide["annotation"]
                    )
                    self.anno_y_axis.visible = self.anno_y.visible

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

                    self.ranked_data.data = ranked_slices

                    def set_range(plot_range, data):
                        if len(data) > 0:
                            start = min(data)
                            end = max(data)
                            size = end - start
                            start -= size * RANGE_PADDING
                            end += size * RANGE_PADDING
                            plot_range.start = start
                            plot_range.end = end

                    def set_log_range(plot_range, data):
                        filtered_data = [x for x in data if x > 0]
                        if len(filtered_data) > 0:
                            start = min(filtered_data)
                            end = max(filtered_data)
                            start *= LOG_PADDING
                            end /= LOG_PADDING
                            plot_range.start = start
                            plot_range.end = end

                    set_range(self.ranked_columns.x_range, ranked_slices["idx_x"])
                    set_log_range(self.ranked_columns.y_range, ranked_slices["xs"])

                    set_range(self.ranked_rows.x_range, ranked_slices["idx_y"])
                    set_log_range(self.ranked_rows.y_range, ranked_slices["ys"])

                    set_log_range(self.ranked_col_and_rows.x_range, ranked_slices["xs"]) # @todo this is not working
                    set_log_range(self.ranked_col_and_rows.y_range, ranked_slices["ys"])

                    self.dist_dep_dec_plot_data.data = dist_dep_dec_plot_data

                    self.custom_hover_x_data.data = bin_coords_x
                    self.custom_hover_y_data.data = bin_coords_y

                    self.set_area_range()

                    for plot in [
                        self.heatmap,
                        self.raw_y,
                        self.raw_y_log,
                        self.anno_y,
                        self.heatmap_x_axis,
                        self.heatmap_x_axis_3,
                    ]:
                        plot.xgrid.bounds = (0, canvas_size_x)
                        plot.xaxis.bounds = (0, canvas_size_x)
                    for plot in [
                        self.heatmap,
                        self.raw_x,
                        self.raw_x_log,
                        self.anno_x,
                        self.heatmap_y_axis,
                        self.heatmap_y_axis_3,
                    ]:
                        plot.ygrid.bounds = (0, canvas_size_y)
                        plot.yaxis.bounds = (0, canvas_size_y)

                    self.curdoc.unhold()
                    end_render_time = time.perf_counter()
                    process_time = "{:,}".format(int(1000 * (end_time - start_time)))
                    render_time = "{:,}".format(
                        int(1000 * (end_render_time - start_render_time))
                    )
                    self.print("Rendering done")
                    end_text = (
                        "Bin Size: "
                        + self.get_readable_bin_size()  #
                        + "\nTime (Process/Render): "
                        + process_time
                        + "ms/"
                        + render_time  #
                        + "ms\nDisplaying "
                        + "{:,}".format(len(d_heatmap["color"]))
                        + " bins"  #
                        + "\nErrors: "
                        + error_text_status  #
                    )
                    self.print_status(end_text)
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
                if self.have_error:
                    self.spinner.text = '<img id="spinner" src="biosmoother/static/error.png" width="30px" height="30px">'
                else:
                    self.spinner.text = '<img id="spinner" src="biosmoother/static/favicon.png" width="30px" height="30px">'
                self.re_layout.text = "a" if self.re_layout.text == "b" else "b"
                if not bin.global_variables.no_save:
                    try:
                        self.session.save_session()
                    except:
                        self.print(
                            "WARNING: could not save session. Do you have write permissions for the index?"
                        )

            self.curdoc.add_next_tick_callback(callback)

        self.undo_button.disabled = not self.session.has_undo()
        self.undo_button.css_classes = [
            "other_button",
            "fa_page_previous"
            if self.undo_button.disabled
            else "fa_page_previous_solid",
            "tooltip", "tooltip_undo", "tooltip_fix_overlap"
        ]
        self.redo_button.disabled = not self.session.has_redo()
        self.redo_button.css_classes = [
            "other_button",
            "fa_page_next" if self.redo_button.disabled else "fa_page_next_solid",
            "tooltip", "tooltip_redo", "tooltip_fix_overlap"
        ]
        yield executor.submit(unlocked_task)

    def trigger_render(self):
        self.session.cancel()
        self.force_render = True

    def render_callback(self):
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
                    (
                        curr_area_size / self.curr_area_size < min_change
                        or MainLayout.area_outside(self.last_drawing_area, curr_area)
                    )
                    and self.session.get_value(["settings", "interface", "do_redraw"])
                ) or self.force_render:
                    if curr_area_size / self.curr_area_size < min_change:
                        s = "Rendering was triggered by zoom-in."
                        self.print(s)
                        self.print_status(s)
                        zoom_in_render = True
                    elif self.force_render:
                        s = "Rendering was triggered by parameter change."
                        self.print(s)
                        self.print_status(s)
                    elif MainLayout.area_outside(self.last_drawing_area, curr_area):
                        s = "Rendering was triggered by panning or zoom-out."
                        self.print(s)
                        self.print_status(s)
                    else:
                        s = "Rendering."
                        self.print(s)
                        self.print_status(s)
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
                self.session.get_value(["settings", "interface", "update_freq", "val"])
                * 1000,
            )
        else:
            self.curdoc.add_timeout_callback(lambda: self.render_callback(), 1000)

    def set_root(self):
        self.curdoc.title = "Smoother"
        self.force_render = True
        self.do_config()
        self.render_callback()

        # very annoying, but we need to trigger a relayout at the beggining once everything is loaded
        # however, i'm not sure how to know once everythin is loaded. I guess JS could send an event...
        # for now we just send a few updates at different timepoints
        def layout_callback():
            self.re_layout.text = "a" if self.re_layout.text == "b" else "b"

        self.curdoc.add_timeout_callback(lambda: layout_callback(), 100)
        for time in range(1, 10):
            self.curdoc.add_timeout_callback(lambda: layout_callback(), time * 1000)
