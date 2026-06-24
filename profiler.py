from datetime import datetime
import logging
import time
from functools import wraps

# TODO thread info

class _Profiler(object):
    def __init__(self):
        self.logger = logging.getLogger("profiler")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            # open log in append mode with UTF-8 to support OCR text characters
            self.handler = logging.FileHandler("profiler.log", encoding="utf-8")
            # set log handlers and formatting
            self.formatter = logging.Formatter("[PROFILE] %(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            self.handler.setFormatter(self.formatter)
            self.logger.addHandler(self.handler)

    # Decorator wrapper function for performance profiling, finding bottlenecks and logging execute and response times
    def time_profile(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)  # run wrapped function
            finally:
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                p = f"'{func.__name__}' took {duration_ms:.2f} ms"
                self.logger.info(p)

            return result
        return wrapper

# singleton global object
profiler = _Profiler()