import argparse
import libsmoother
import bokeh.command.subcommands.serve as bcss
import site
import os
from pathlib import Path

def serve(args):
    from smoother.bin import global_variables
    os.environ["smoother_index_path"] = args.index_prefix
    os.environ["smoother_port"] = str(args.port)
    smoother_path = os.fspath(Path(os.path.join(site.getsitepackages()[0], "smoother")).resolve())
    args.files = [smoother_path]
    args.log_level = "error"
    bcss.Serve(parser=argparse.ArgumentParser()).invoke(args)

def add_parsers(main_parser):
    parser = main_parser.add_parser(
        "serve", help="Serve a smoother index."
    )
    parser.add_argument(
        "index_prefix",
        help="Path where the index shall be loaded from.",
    )

    def filter_args(args):
        for name, a in args:
            if name not in set([
                "--show",
                "--port",
                "--address",
                "--allow-websocket-origin",
            ]) and not "smoother_dont_hide_args" in os.environ:
                a["help"] = argparse.SUPPRESS
            yield name, a

    for arg in filter_args(bcss.Serve.args):
            flags, spec = arg
            if not isinstance(flags, tuple):
                flags = (flags,)
            if not isinstance(spec, dict):
                kwargs = dict(entries(spec))
            else:
                # NOTE: allow dict for run time backwards compatibility, but don't include in types
                kwargs = spec
            parser.add_argument(*flags, **kwargs)


    parser.set_defaults(func=serve)


def make_main_parser():
    parser = argparse.ArgumentParser(description="")
    sub_parsers = parser.add_subparsers(
        help="Sub-command that shall be executed.", dest="cmd"
    )
    sub_parsers.required = True
    add_parsers(sub_parsers)
    libsmoother.indexer_parser.add_parsers(sub_parsers)
    return parser

def main():
    parser = make_main_parser()

    args = parser.parse_args()

    args.func(args)

if __name__ == "__main__":
    main()