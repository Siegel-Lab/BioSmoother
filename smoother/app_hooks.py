import os
from libsmoother import Quarry
import bin.global_variables
import json
NUM_SESSIONS = 0
import os


def on_server_loaded(server_context):
    path = None
    if not "smoother_index_path" in os.environ["smoother_index_path"]:
        if os.path.exists(os.environ["smoother_index_path"]):
            path = os.environ["smoother_index_path"]
        if os.path.exists(os.environ["smoother_index_path"] + ".smoother_index/"):
            path = os.environ["smoother_index_path"] + ".smoother_index/"
        if not path is None:
            print("loading index...")
            bin.global_variables.quarry_session = Quarry(path)
            bin.global_variables.quarry_session.allow_ctrl_c_cancel = False

            if bin.global_variables.quarry_session.get_value(["settings"]) is None:
                with open('smoother/static/conf/default.json', 'r') as f:
                    settings = json.load(f)
                #print(settings)
                bin.global_variables.quarry_session.set_value(["settings"], settings)

            print("done loading.")
        else:
            print("Index file", os.environ["smoother_index_path"], "not found.")
            print("exiting.")
            exit()
    else:
        print("No index path is given.")
        print("exiting.")
        exit()

    # If present, this function executes when the server starts.
    print("starting smoother server at: http://localhost:", os.environ["smoother_port"], "/smoother", sep="")
    print("")
    print("For Clusters:")
    print("\tIf you log in via SSH into your cluster and want to run smoother there,")
    print("\tyou need to forward Smoothers port from your local machine.")
    print("\tPorts can be forwarded using the SSH command option -L.")
    print("\tI.e. log in to your cluster with another terminal using this command: ssh -L ", 
            os.environ["smoother_port"], ":localhost:", 
            os.environ["smoother_port"], " <your_server_addr>", sep="")

def on_server_unloaded(server_context):
    # If present, this function executes when the server shuts down.
    pass

def on_session_created(session_context):
    global NUM_SESSIONS
    # If present, this function executes when the server creates a session.
    NUM_SESSIONS += 1

def on_session_destroyed(session_context):
    global NUM_SESSIONS
    NUM_SESSIONS -= 1
    if NUM_SESSIONS == 0:
        print("closing server since session exited")
        # This function executes when the user closes the session.
        exit()