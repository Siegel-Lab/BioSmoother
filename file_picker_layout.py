from bokeh.layouts import grid, row, column
from bokeh.plotting import figure, curdoc
from bokeh.models.tools import ToolbarBox, ProxyToolbar
from bokeh.models import ColumnDataSource, Dropdown, Button, RangeSlider, Slider, FileInput, TextInput, MultiChoice, FuncTickFormatter, Div, HoverTool
import math
from datetime import datetime
from tornado import gen
from bokeh.document import without_document_lock
from bokeh.models import Panel, Tabs
from bokeh.models import Range1d
import os
from bokeh.palettes import Viridis256, Category10
from datetime import datetime, timedelta
import preprocess
from bokeh.document import without_document_lock
from main_layout import *



class FilePickerLayout:
    def __init__(self):
        self.curdoc = curdoc()

        self.root = None
        self.interaction_file_list = []
        self.normalization_file_list = []


        self.chr_lengths_file = TextInput()
        self.anno_file = TextInput()

        self.more_interaction_button = Button(label="add interaction file")
        def event(e):
            self.add_interaction()
            self.set_root()
        self.more_interaction_button.on_click(event)
        self.more_normalization_button = Button(label="add normalization file")
        def event(e):
            self.add_normalization()
            self.set_root()
        self.more_normalization_button.on_click(event)


        def event(e):
            self.run_setup()
        self.run = Button(label="Run", button_type="success")
        self.run.on_click(event)
        def event(e):
            self.test_setup()
        self.test = Button(label="TestSetup", button_type="success")
        self.test.on_click(event)

        self.add_interaction()
        self.add_normalization()


    def add_interaction(self):
        but = Button(label="remove")
        def event(e):
            idx = 0
            for i, (_, _, _, b) in enumerate(self.interaction_file_list):
                if but == b:
                    idx = i
                    break
            del self.interaction_file_list[idx]
            self.set_root()
        but.on_click(event)
        self.interaction_file_list.append((TextInput(), TextInput(), MultiChoice(options=["group a", "group b"]), but))

    def add_normalization(self):
        but = Button(label="remove")
        def event(e):
            idx = 0
            for i, (_, _, _, b) in enumerate(self.normalization_file_list):
                if but == b:
                    idx = i
                    break
            del self.normalization_file_list[idx]
            self.set_root()
        but.on_click(event)
        self.normalization_file_list.append((TextInput(), TextInput(), MultiChoice(options=["row", "col"]), but))

    
    def set_root(self):
        l = []
        for x, y, z, v in self.interaction_file_list:
            l.append(
                row([Div(text="Label:"), x, Div(text="Path:"), y, Div(text="Group(s):"), z, v])
            )
        l2 = []
        for x, y, z, v in self.normalization_file_list:
            l2.append(
                row([Div(text="Label:"), x, Div(text="Path:"), y, Div(text="Axis/Axes:"), z, v])
            )
        r1 = row([Div(text="Chromosome Lengths:"), self.chr_lengths_file])
        r2 = row([Div(text="Annotations:"), self.anno_file])
        self.root = column([r1, r2] + l + [self.more_interaction_button] + l2 + 
                           [self.more_normalization_button, self.run, self.test])
        self.curdoc.clear()
        self.curdoc.add_root(self.root)

    def run_setup(self):
        desc = ""
        chr_len = self.chr_lengths_file.value
        annos = self.anno_file.value
        desc += chr_len + "\n"
        desc += annos + "\n"
        inters = []
        for x, y, z, _ in self.interaction_file_list:
            if "group a" in z.value:
                if "group b" in z.value:
                    j = "both"
                else:
                    j = "a"
            else:
                if "group b" in z.value:
                    j = "b"
                else:
                    j = "neither"
            inters.append((y.value, x.value, j))
        norm = []
        for x, y, z, _ in self.normalization_file_list:
            if "row" in z.value:
                if "vol" in z.value:
                    j = "both"
                else:
                    j = "row"
            else:
                if "group b" in z.value:
                    j = "col"
                else:
                    j = "neither"
            norm.append((y.value, x.value, j))
        
        print("loading")
        meta, tree, t_n = preprocess.preprocess(desc, "", chr_len, annos, inters, norm)
        MainLayout(meta, tree, t_n).set_root()

    def test_setup(self):
        bed_folder = "/work/project/ladsie_012/ABS.2.2/2021-10-26_NS502-NS521_ABS_CR_RADICL_inputMicroC/bed_files"
        bed_suffix = "RNA.sorted.bed_K1K2.bed_K4.bed_R_D.bed_R_D_K1K2.bed_R_D_PRE1.bed"
        bam_folder = "/work/project/ladsie_012/ABS.2.2/20210608_Inputs"
        bam_suffix="R1.sorted.bam"
        meta, tree, t_n = preprocess.preprocess(
            "", "out/mini", "heatmap_server/Lister427.sizes", 
            "heatmap_static/HGAP3_Tb427v10_merged_2021_06_21.gff3", [
            (bed_folder + "/NS504_P10_Total_3." + bed_suffix, "P10_Total_Rep3", "a"),
            (bed_folder + "/NS505_N50_Total_1." + bed_suffix, "P10_Total_Rep1", "a"),
            (bed_folder + "/NS508_P10_NPM_1." + bed_suffix, "P10_NPM_Rep1", "b"),
            (bed_folder + "/NS511_N50_NPM_1." + bed_suffix, "N50_NPM_Rep1", "b"),
        ], [
            (bam_folder + "/WT1_gDNA_inputATAC." + bam_suffix, "gDNA_inputATAC", "col"),
            (bam_folder + "/WT1_RNAseq_NS320." + bam_suffix, "RNAseq_NS320", "row"),
        ])
        MainLayout(meta, tree, t_n).set_root()