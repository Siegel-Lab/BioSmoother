import os
from libbiosmoother import Index
import bin.global_variables
import json
import os

try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources


def on_server_loaded(server_context):
    global smoother_index
    if not "biosmoother_no_save" in os.environ:
        print(
            "biosmoother expects biosmoother_no_save environment variable to be set but it was not"
        )
    else:
        bin.global_variables.no_save = os.environ["biosmoother_no_save"] == "True"
    if not "biosmoother_keep_alive" in os.environ:
        print(
            "biosmoother expects biosmoother_keep_alive environment variable to be set but it was not"
        )
    else:
        bin.global_variables.keep_alive = os.environ["biosmoother_keep_alive"] == "True"
    if not "biosmoother_quiet" in os.environ:
        print(
            "biosmoother expects biosmoother_quiet environment variable to be set but it was not"
        )
    else:
        bin.global_variables.quiet = os.environ["biosmoother_quiet"] == "True"

    path = None
    if "biosmoother_index_path" in os.environ:
        if os.path.exists(os.environ["biosmoother_index_path"]):
            path = os.environ["biosmoother_index_path"]
        if os.path.exists(os.environ["biosmoother_index_path"] + ".biosmoother_index/"):
            path = os.environ["biosmoother_index_path"] + ".biosmoother_index/"
        if not path is None:
            print("loading index...")
            biosmoother_index = Index(path)

            bin.global_variables.biosmoother_index = biosmoother_index

            print("done loading.")
        else:
            print(
                "index", os.environ["biosmoother_index_path"], "does not exist, exiting"
            )
            exit()
    else:
        print("No index path is given.")
        print("exiting.")
        exit()

    # If present, this function executes when the server starts.
    print(
        "starting biosmoother server at: http://localhost:",
        os.environ["biosmoother_port"],
        "/biosmoother",
        sep="",
    )


def on_server_unloaded(server_context):
    # If present, this function executes when the server shuts down.
    pass


def on_session_created(session_context):
    # If present, this function executes when the server creates a session.
    bin.global_variables.NUM_SESSIONS += 1


def on_session_destroyed(session_context):
    bin.global_variables.NUM_SESSIONS -= 1
    if not bin.global_variables.keep_alive:
        if bin.global_variables.NUM_SESSIONS == 0:
            print("closing server since session exited")
            # This function executes when the user closes the session.
            exit()
