from datetime import datetime, timedelta
import psutil

class Logger:
    def __init__(self):
        self.render_curr_step = 0
        self.render_reason = ""
        self.render_last_step = None
        self.render_last_time = None
        self.render_time_record = []
    
    def new_render(self, reason, callback= lambda x: print(x)):
        self.render_curr_step = 0
        self.render_time_record = []
        if not reason is None:
            self.render_reason = reason
            self.render_step_log(callback=callback)

    def render_step_log(self, step_name="", sub_step=0, sub_step_total=None,
                        callback= lambda x: print(x)):
        if self.render_last_step is None or self.render_last_step != step_name:
            if self.render_last_step != step_name:
                self.render_curr_step += 1
            self.render_last_step = step_name
            if not len(step_name) == 0:
                if len(self.render_time_record) > 0:
                    self.render_time_record[-1][1] = datetime.now() - \
                        self.render_time_record[-1][1]
                self.render_time_record.append([step_name, datetime.now()])
        if self.render_last_time is None or (datetime.now() - self.render_last_time).seconds >= 1:
            self.render_last_time = datetime.now()
            s = "rendering due to " + self.render_reason + "."
            if len(step_name) > 0:
                s += " Step " + str(self.render_curr_step) + \
                    " " + str(step_name) + ". Substep " + str(sub_step)
                if not sub_step_total is None:
                    s += " of " + str(sub_step_total) + " = " + str((100*sub_step)//sub_step_total) + "%. "
                if len(self.render_time_record) > 0:
                    s += " Runtime: " + str(datetime.now() - self.render_time_record[-1][1])
                callback(s)

    def render_done(self, bin_amount):
        if len(self.render_time_record) > 0:
            self.render_time_record[-1][1] = datetime.now() - \
                self.render_time_record[-1][1]
        print("render done, used time:\033[K")
        total_time = timedelta()
        for x in self.render_time_record:
            total_time += x[1]
        for idx, (name, time) in enumerate(self.render_time_record):
            print("step " + str(idx), str(time),
                  str(int(100*time/total_time)) + "%", name, "\033[K", sep="\t")
        ram_usage = psutil.virtual_memory().percent
        print("Currently used RAM:", ram_usage, "%\033[K")
        print("Number of displayed bins:", bin_amount, "\033[K")
        return total_time, ram_usage