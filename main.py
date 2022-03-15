__author__ = "Markus Schmidt"
__version__ = "1.1.0"
__email__ = "Markus.Schmidt@lmu.de"

from main_layout import *
from bokeh.plotting import curdoc

#FilePickerLayout().set_root()

def cleanup_session(session_context):
    print("closing server since session exited")
    # This function executes when the user closes the session.
    exit()

curdoc().on_session_destroyed(cleanup_session)

MainLayout().set_root()