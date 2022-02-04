from xmlrpc.client import Boolean
from bokeh.models import FuncTickFormatter
from bokeh.core.properties import Float, List
from bokeh.util.compiler import TypeScript
from bokeh.models import BasicTicker

TS_CODE = """
import * as p from "core/properties"
import {TickSpec} from "models/tickers/ticker"
import {BasicTicker } from "models/tickers/basic_ticker"

export namespace ExtraTicksTicker {
  export type Attrs = p.AttrsOf<Props>
  export type Props = BasicTicker.Props & {
    extra_ticks: p.Property<Array<number>>
  }
}

export interface ExtraTicksTicker extends ExtraTicksTicker.Attrs {}

export class ExtraTicksTicker extends BasicTicker {
  properties: ExtraTicksTicker.Props

  constructor(attrs?: Partial<ExtraTicksTicker.Attrs>) {
    super(attrs)
  }

  static init_ExtraTicksTicker(): void {
    this.define<ExtraTicksTicker.Props>(({Number, Array}) => ({
      extra_ticks: [ Array(Number), [] ],
    }))
  }

  get_ticks_no_defaults(data_low: number, data_high: number, cross_loc: any, desired_n_ticks: number): TickSpec<number> {
    return {
        major: this.extra_ticks,
        minor: super.get_ticks_no_defaults(data_low, data_high, cross_loc, desired_n_ticks).major,
    }
  }

}
"""


class ExtraTicksTicker(BasicTicker):
    __implementation__ = TypeScript(TS_CODE)
    extra_ticks = List(Float)


class ChrSizes:
    def longest_common_suffix(self, l):
        s = ""
        min_l = min(len(x) for x in l)
        while len(s) < min_l:
            sn = l[0][-(len(s)+1)] + s
            for x in l:
                if x[-len(sn)] != sn[0]:
                    return s
            s = sn
        return s

    def __init__(self, file_name, filter=lambda x: True):
        # load the exact chr lenghts from file
        self.chr_order = []
        self.chr_sizes = {}
        self.chr_sizes_l = []
        with open(file_name, "r") as len_file:
            for line in len_file:
                chr_name, chr_len = line.split("\t")
                if filter(chr_name):
                    self.chr_order.append(chr_name)
                    self.chr_sizes[chr_name] = int(chr_len)
                    self.chr_sizes_l.append(int(chr_len))
                else:
                    print("filtered out", chr_name)

        self.lcs = self.longest_common_suffix(self.chr_order)

        # compute offset of the chromosomes
        self.chr_start_pos = {}
        self.chr_starts = []
        last_offset = 0
        for chr_x in self.chr_order:
            self.chr_start_pos[chr_x] = last_offset
            self.chr_starts.append(last_offset)
            # round up to the next full bin
            last_offset += self.chr_sizes[chr_x]
        self.chr_start_pos["end"] = last_offset


    def coordinate(self, x, chr):
        return self.chr_start_pos[chr] + x

    def setup(self, main_layout):
        main_layout.heatmap.x_range.start = 0
        main_layout.heatmap.x_range.end = self.chr_start_pos["end"]
        main_layout.heatmap.y_range.start = 0
        main_layout.heatmap.y_range.end = self.chr_start_pos["end"]
        main_layout.heatmap.x_range.reset_start = 0
        main_layout.heatmap.x_range.reset_end = self.chr_start_pos["end"]
        main_layout.heatmap.y_range.reset_start = 0
        main_layout.heatmap.y_range.reset_end = self.chr_start_pos["end"]

        formater = FuncTickFormatter(
            args={"contig_starts": [self.chr_start_pos[chr_x] for chr_x in self.chr_order],
                  "genome_end": self.chr_start_pos["end"],
                  "contig_names": [x[:-len(self.lcs)] for x in self.chr_order]},
            code="""
                            if(tick < 0 || tick >= genome_end)
                                return "n/a";
                            var idx = 0;
                            while(contig_starts[idx + 1] <= tick)
                                idx += 1;
                            return contig_names[idx] + ": " + (tick - contig_starts[idx]);
                        """)
        main_layout.heatmap_y_axis.yaxis[0].formatter = formater
        main_layout.heatmap_x_axis.xaxis[0].formatter = formater

        ticker_border = ExtraTicksTicker(
            extra_ticks=[self.chr_start_pos[chr_x]
                         for chr_x in self.chr_order] + [self.chr_start_pos["end"]],
        )
        ticker_border.min_interval = 1
        # ticker_center = ExtraTicksTicker(
        #    extra_ticks=[self.chr_start_pos[chr_x] + self.chr_sizes[chr_x]/2 for chr_x in self.chr_order])

        for plot in [main_layout.heatmap, main_layout.ratio_y, main_layout.raw_y, main_layout.anno_y,
                     main_layout.heatmap_x_axis]:
            plot.xgrid.minor_grid_line_alpha = plot.ygrid.grid_line_alpha
            plot.xgrid.minor_grid_line_color = plot.xgrid.grid_line_color
            plot.xgrid.grid_line_color = "darkgrey"
            plot.xgrid.ticker = ticker_border
            plot.xgrid.bounds = (0, self.chr_start_pos["end"])
            plot.xaxis.bounds = (0, self.chr_start_pos["end"])
            plot.xaxis.major_label_text_align = "left"
            plot.xaxis.ticker.min_interval = 1
        for plot in [main_layout.heatmap, main_layout.ratio_x, main_layout.raw_x, main_layout.anno_x,
                     main_layout.heatmap_y_axis]:
            plot.ygrid.minor_grid_line_alpha = plot.ygrid.grid_line_alpha
            plot.ygrid.minor_grid_line_color = plot.ygrid.grid_line_color
            plot.ygrid.grid_line_color = "darkgrey"
            plot.ygrid.ticker = ticker_border
            plot.ygrid.bounds = (0, self.chr_start_pos["end"])
            plot.yaxis.bounds = (0, self.chr_start_pos["end"])
            plot.yaxis.major_label_text_align = "right"
            plot.yaxis.ticker.min_interval = 1

    def bin_cols_or_rows(self, h_bin, start=0, end=None, none_for_chr_border=False):
        if end is None:
            end = self.chr_start_pos["end"]
        h_bin = max(1, h_bin)
        ret = []
        ret_2 = []
        x_chrs = [idx for idx, (c_start, c_size) in enumerate(zip(self.chr_starts, self.chr_sizes_l))
                  if c_start <= end and c_start + c_size >= start and c_size*10 >= h_bin]
        if none_for_chr_border:
            ret.append(None)
            ret_2.append(None)
        for x_chr in x_chrs:
            x_start = self.chr_starts[x_chr]
            x = max(int(start), x_start)
            x_end = self.chr_starts[x_chr] + self.chr_sizes_l[x_chr]
            while x <= min(end, x_end):
                ret.append((x, min(h_bin, x_end - x)))
                ret_2.append((self.chr_order[x_chr], x + x_start))
                x += h_bin
            if none_for_chr_border:
                ret.append(None)
                ret_2.append(None)
        return ret, ret_2
