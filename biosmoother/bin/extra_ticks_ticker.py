from bokeh.core.properties import Float, List
from bokeh.util.compiler import TypeScript
from bokeh.models import AdaptiveTicker


TS_CODE = """
import * as p from "core/properties"
import {TickSpec} from "models/tickers/ticker"
import {AdaptiveTicker } from "models/tickers/adaptive_ticker"

export namespace ExtraTicksTicker {
  export type Attrs = p.AttrsOf<Props>
  export type Props = AdaptiveTicker.Props & {
    extra_ticks: p.Property<Array<number>>
  }
}

export interface ExtraTicksTicker extends ExtraTicksTicker.Attrs {}

export class ExtraTicksTicker extends AdaptiveTicker {
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


class ExtraTicksTicker(AdaptiveTicker):
    __implementation__ = TypeScript(TS_CODE)
    extra_ticks = List(Float)


TS_CODE_2 = """
import * as p from "core/properties"
import {TickSpec} from "models/tickers/ticker"
import {AdaptiveTicker } from "models/tickers/adaptive_ticker"

export namespace IntermediateTicksTicker {
  export type Attrs = p.AttrsOf<Props>
  export type Props = AdaptiveTicker.Props & {
    extra_ticks: p.Property<Array<number>>
  }
}

export interface IntermediateTicksTicker extends IntermediateTicksTicker.Attrs {}

export class IntermediateTicksTicker extends AdaptiveTicker {
  properties: IntermediateTicksTicker.Props

  constructor(attrs?: Partial<IntermediateTicksTicker.Attrs>) {
    super(attrs)
  }

  static init_IntermediateTicksTicker(): void {
    this.define<IntermediateTicksTicker.Props>(({Number, Array}) => ({
      extra_ticks: [ Array(Number), [] ],
    }))
  }

  get_ticks_no_defaults(data_low: number, data_high: number): TickSpec<number> {
    let ret_ticks: number[];
    let empty: number[];
    ret_ticks = [];
    empty = [];
    for(var i = 0; i < this.extra_ticks.length - 1; i++)
        if(Math.max(data_low, this.extra_ticks[i]) < Math.min(data_high, this.extra_ticks[i + 1]))
            ret_ticks.push((Math.max(data_low, this.extra_ticks[i])
                            + Math.min(data_high, this.extra_ticks[i + 1])) / 2);
    return {
        major: ret_ticks,
        minor: empty,
    }
  }

}
"""


class IntermediateTicksTicker(AdaptiveTicker):
    __implementation__ = TypeScript(TS_CODE_2)
    extra_ticks = List(Float)
