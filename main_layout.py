from bokeh.layouts import gridplot
from bokeh.plotting import figure, curdoc

class MainLayout:
    def __init__(self):
        self.heaptmap = figure()

        self.root = gridplot([[self.heaptmap]], sizing_mode="stretch_both")

    def set_root(self):
        curdoc().clear()
        curdoc().add_root(self.root)
