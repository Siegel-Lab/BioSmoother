import argparse
import libsmoother
import bokeh.command.subcommands.serve as bcss
import os
from pathlib import Path
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources

def serve(args):
    import smoother
    args.files = [Path(smoother.__file__).parent]

    os.environ["smoother_index_path"] = args.index_prefix
    os.environ["smoother_port"] = str(args.port)
    os.environ["smoother_no_save"] = str(args.no_save)
    os.environ["smoother_keep_alive"] = str(args.keep_alive)
    os.environ["smoother_quiet"] = str(args.quiet)

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
    parser.add_argument('-s', '--no_save', action='store_true',
                        help="Disable saving custom settings or sessions. This is intended for hosting public example datasets. (default: off)")
    parser.add_argument('-k', '--keep_alive', action='store_true',
                        help="Keep the server alive even if the last browser window has been closed. (default: off)")
    parser.add_argument('-q', '--quiet', action='store_true',
                        help="Print less on the command line. (default: off)")

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

    parser.add_argument('-v', '--version', action='version',
                        version=(pkg_resources.files("smoother") / "VERSION").read_text())
    parser.add_argument('--version_lib', action='version', help=argparse.SUPPRESS,
                        version=libsmoother._import_lib_smoother_cpp.LIB_SMOOTHER_CPP_VERSION)
    parser.add_argument('--version_sps', action='version', help=argparse.SUPPRESS,
                        version=libsmoother._import_lib_smoother_cpp.SPS_VERSION)

    args = parser.parse_args()

    args.func(args)

if __name__ == "__main__":
    main()