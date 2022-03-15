
NUM_SESSIONS = 0


def on_server_loaded(server_context):
    # If present, this function executes when the server starts.
    pass

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