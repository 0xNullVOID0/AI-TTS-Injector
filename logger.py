from datetime import datetime
import sys

class ConsoleLogger:
    def __init__(self, log_filename="console_output.log"):
        # store original streams so we can still print to the actual terminal
        self.terminal_out = sys.stdout
        self.terminal_err = sys.stderr

        # open log in append mode with UTF-8 to support OCR text characters
        self.log_file = open(log_filename, "a", encoding="utf-8")

        # session seperator
        self.log_file.write(f"\n--- SESSION STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        self.log_file.flush()

    def write(self, message):
        self.terminal_out.write(message)
        self.log_file.write(message)
        self.log_file.flush() # flush instantly so crashes or freezes don't prevent saving

    def flush(self):
        # required for Python stream compatibility
        self.terminal_out.flush()
        self.log_file.flush()


# Hijacks and captures all stdout and stderr globally across all scripts/modules
sys.stdout = ConsoleLogger()
sys.stderr = sys.stdout