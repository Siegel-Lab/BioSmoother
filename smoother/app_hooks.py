import os
from libsmoother import Index, open_default_json
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
    if not "smoother_no_save" in os.environ:
        print(
            "smoother expects smoother_no_save environment variable to be set but it was not"
        )
    else:
        bin.global_variables.no_save = os.environ["smoother_no_save"] == "True"
    if not "smoother_keep_alive" in os.environ:
        print(
            "smoother expects smoother_keep_alive environment variable to be set but it was not"
        )
    else:
        bin.global_variables.keep_alive = os.environ["smoother_keep_alive"] == "True"
    if not "smoother_quiet" in os.environ:
        print(
            "smoother expects smoother_quiet environment variable to be set but it was not"
        )
    else:
        bin.global_variables.quiet = os.environ["smoother_quiet"] == "True"

    path = None
    if "smoother_index_path" in os.environ:
        if os.path.exists(os.environ["smoother_index_path"]):
            path = os.environ["smoother_index_path"]
        if os.path.exists(os.environ["smoother_index_path"] + ".smoother_index/"):
            path = os.environ["smoother_index_path"] + ".smoother_index/"
        if not path is None:
            print("loading index...")
            smoother_index = Index(path)

            if smoother_index.get_value(["settings"]) is None:
                with open_default_json() as f:
                    settings = json.load(f)
                # print(settings)
                smoother_index.set_value(["settings"], settings)

            bin.global_variables.smoother_index = smoother_index

            print("done loading.")
        else:
            print("index", os.environ["smoother_index_path"], "does not exist, exiting")
            exit()
    else:
        print("No index path is given.")
        print("exiting.")
        exit()

    # If present, this function executes when the server starts.
    print(
        "starting smoother server at: http://localhost:",
        os.environ["smoother_port"],
        "/smoother",
        sep="",
    )
    print("")
    print("For Clusters:")
    print("\tIf you log in via SSH into your cluster and want to run smoother there,")
    print("\tyou need to forward Smoothers port from your local machine.")
    print("\tPorts can be forwarded using the SSH command option -L.")
    print(
        "\tI.e. log in to your cluster with another terminal using this command: ssh -L ",
        os.environ["smoother_port"],
        ":localhost:",
        os.environ["smoother_port"],
        " <your_server_addr>",
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
