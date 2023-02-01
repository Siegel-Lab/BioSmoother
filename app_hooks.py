import os
from libsmoother import Quarry
import bin.global_variables
import json
NUM_SESSIONS = 0


def on_server_loaded(server_context):
    if os.path.exists(os.environ["smoother_index_path"] + ".smoother_index/"):
        print("loading index...")
        bin.global_variables.quarry_session = Quarry(os.environ["smoother_index_path"] + ".smoother_index")
        #self.session.print_callback = lambda s: self.print(s)

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

    # If present, this function executes when the server starts.
    print("starting smoother server at: http://localhost:", os.environ["smoother_port"], "/smoother", sep="")
    print("")
    print("For Clusters:")
    print("\tIf you log in via SSH into your cluster and want to run smoother there,")
    print("\tyou need to forward Smoothers port from your local machine.")
    print("\tPorts can be forwarded using the SSH command option -L.")
    print("\tI.e. log in to your cluster with another terminal using this command: ssh -L ", os.environ["smoother_port"], ":localhost:", os.environ["smoother_port"], " <your_server_addr>", sep="")

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