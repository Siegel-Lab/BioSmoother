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