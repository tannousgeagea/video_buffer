import time

class KeepTrackOfTime:
    def __init__(self):
        self.what_is_the_time = time.time()

    def check_if_time_less_than_diff(self, start, end, diff=1):
        return (end - start) < diff
    
    def check_if_time_more_than_diff(self, start, end, diff=1):
        return (end - start) > diff
    
    def update_time(self, new=None):
        self.what_is_the_time = new if new is not None else time.time()