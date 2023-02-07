import argparse


def serve(args):
    import bokeh.command.subcommands.serve as bcss
    from bokeh.command.subcommand import Subcommand
    bcss.Serve(parser=argparse.ArgumentParser()).invoke(args)

def add_parsers(main_parser):
    parser = main_parser.add_parser(
        "serve", help="serve a smoother index"
    )
    parser.add_argument(
        "index_prefix",
        help="Path where the index shall be loaded from.",
    )
    parser.set_defaults(func=serve)