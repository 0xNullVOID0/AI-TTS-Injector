from datetime import datetime
import inspect
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
    # logs the arguments of each call automatically, so the ms values can be compared per call
    def time_profile(self, func=None, *, max_arg_len=310):
        if func is None:
            return lambda f: self.time_profile(f, max_arg_len=max_arg_len)

        # methods receive the instance as first arg, which is skipped so its repr is never called
        is_method = "." in func.__qualname__
        # parameter names resolved once at decoration time, not on every call
        names = [p for p in inspect.signature(func).parameters]
        if is_method:
            names = names[1:]

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)  # run wrapped function
            finally:
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                # ms first so the values line up for comparison, arguments of this specific call after
                try:
                    shown = args[1:] if is_method else args
                    args_text = self._format_args(shown, kwargs, names, max_arg_len)
                except Exception as e:
                    args_text = f"<unavailable: {e}>"
                self.logger.info(f"'{func.__name__}' took {duration_ms:.2f} ms | args: {args_text}")

            return result
        return wrapper

    @staticmethod
    def _format_args(args, kwargs, names, max_len):
        parts = []
        for i, a in enumerate(args):
            try:
                value = repr(a)
            except Exception:
                value = f"<{type(a).__name__}>"
            parts.append((names[i] if i < len(names) else None, value))
        parts += list(kwargs.items())  # kwargs already carry their own names
        # collapse newlines and indentation (numpy arrays repr across many lines) into one line per value
        formatted = []
        for name, value in parts:
            value = " ".join(str(value).split())
            # shorten each value on its own so one long argument never hides the others
            if len(value) > max_len:
                value = value[:max_len] + "..."
            formatted.append(f"{name}={value}" if name else value)
        return ", ".join(formatted)



# singleton global object
profiler = _Profiler()