import argparse
import libbiosmoother
import bokeh.command.subcommands.serve as bcss
import os
from pathlib import Path

try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources

def get_path(prefix):
    for possible in [prefix, prefix + ".smoother_index"]:
        if os.path.exists(possible) and os.path.isdir(possible):
            return possible
    raise RuntimeError("the given index " + prefix + " does not exist.")

def serve(args):
    import biosmoother

    args.files = [Path(biosmoother.__file__).parent]

    os.environ["biosmoother_index_path"] = get_path(args.index_prefix)
    os.environ["biosmoother_port"] = str(args.port)
    os.environ["biosmoother_no_save"] = str(args.no_save)
    os.environ["biosmoother_keep_alive"] = str(args.keep_alive)
    os.environ["biosmoother_quiet"] = str(args.quiet)

    args.log_level = "error"

    bcss.Serve(parser=argparse.ArgumentParser()).invoke(args)


def add_parsers(main_parser):
    parser = main_parser.add_parser(
        "serve",
        help="Open Smoother's graphical user interface and launch an exisiting existing index. If an index has been already launched before, the session will be restored with the parameters of the last session.",
    )
    parser.add_argument(
        "index_prefix",
        help="Path to the index directory generated with the init command.",
    )
    parser.add_argument(
        "-s",
        "--no_save",
        action="store_true",
        help="Disable saving changes to the current session. This is intended for hosting public datasets (default: off)",
    )
    parser.add_argument(
        "-k",
        "--keep_alive",
        action="store_true",
        help="Keep Smoother alive when it's browser tab is closed. Smoother then can be reopened from the link without re-running the serve command. (default: off)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Print less information about the ongoing processes on the command line. (default: off)",
    )

    def filter_args(args):
        for name, a in args:
            if (
                name
                not in set(
                    [
                        "--show",
                        "--port",
                        "--address",
                        "--allow-websocket-origin",
                    ]
                )
                and not "biosmoother_dont_hide_args" in os.environ
            ):
                a["help"] = argparse.SUPPRESS
            else:
                a["help"] = {
                    "--show": "Immediateley open a browser tab for the served index. Only works if run locally.",
                    "--port": "Use a particular port.",
                    "--address": "Use a particular address.",
                    "--allow-websocket-origin": "Public hostnames which may connect to the Smoother server. Check https://docs.bokeh.org/en/latest/docs/user_guide/server/deploy.html#security for more details.",
                }[name]
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
    libbiosmoother.cli.add_parsers(sub_parsers)
    return parser


def make_versioned_parser():
    parser = make_main_parser()

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=(pkg_resources.files("biosmoother") / "VERSION").read_text(),
        help="Print Smoother's version and exit.",
    )
    parser.add_argument(
        "--version_lib",
        action="version",
        help=argparse.SUPPRESS,
        version=libbiosmoother._import_lib_bio_smoother_cpp.LIB_BIO_SMOOTHER_CPP_VERSION,
    )
    parser.add_argument(
        "--version_sps",
        action="version",
        help=argparse.SUPPRESS,
        version=libbiosmoother._import_lib_bio_smoother_cpp.SPS_VERSION,
    )
    parser.add_argument(
        "--compiler_id",
        action="version",
        help=argparse.SUPPRESS,
        version=libbiosmoother._import_lib_bio_smoother_cpp.COMPILER_ID,
    )
    return parser


def main():
    parser = make_versioned_parser()

    args = parser.parse_args()

    args.func(args)


if __name__ == "__main__":
    main()
