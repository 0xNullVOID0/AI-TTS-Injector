import os
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse

from config_handler import config
from profiler import profiler

API_HOST = config.get("KOKORO_HOST")
API_PORT = config.get("KOKORO_PORT")
KOKORO_FOLDER = config.get(f"KOKORO_FOLDER")
KOKORO_START_SCRIPT = config.get(f"KOKORO_START_SCRIPT")

# the terminal command to start the API and load the model
START_COMMAND = [sys.executable, "-m", "uvicorn", "kokoro_fastapi.main:app", f"--port={API_PORT}"]

# Makes sure host and port are correct and properly formatted
def clean_host(host, port):
    host = str(host)

    # parse url properly
    if "://" in host:
        parsed = urlparse(host)
        host = parsed.hostname or "127.0.0.1"
        if parsed.port:
            port = parsed.port

    # change common placeholders since they can cause errors unlike 127.0.0.1
    if host in ["localhost", "http://localhost", "0.0.0.0"]:
        host = "127.0.0.1"

    # make sure port is int instead of string
    try:
        port = int(port)
    except (TypeError, ValueError):
        port = 8880  # fallback to Kokoro's default if parsing breaks

    return host, port


@profiler.time_profile
# Check if port is already open
def is_api_running(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        host, port = clean_host(host, port)

        # network connection check
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                return s.connect_ex((host, port)) == 0
            except Exception:
                return False

@profiler.time_profile
def boot_backend_api():
    if is_api_running(API_HOST, API_PORT):
        print(f"[Kokoro API] is already running on port {API_PORT}, Connecting...")
        return None

    print(f"[Kokoro API] not detected, BOOTING it up automatically...")
    try:
        script_path = f"{KOKORO_FOLDER}/{KOKORO_START_SCRIPT}"

        START_COMMAND = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path
        ]

        # create seperate environment for kokoro and it's scripts
        clean_env = os.environ.copy()

        # clean new environment variables
        clean_env.pop("VIRTUAL_ENV", None)
        clean_env.pop("PYTHONHOME", None)
        clean_env.pop("PYTHONPATH", None)

        # clean system PATH variable this projects .venv\Scripts folder
        if "PATH" in clean_env:
            paths = clean_env["PATH"].split(os.pathsep)
            clean_paths = [p for p in paths if "AI-TTS-Injector" not in p]
            clean_env["PATH"] = os.pathsep.join(clean_paths)

        # force uv to ignore this projects workspace entirely, stripping all automatic parent folder stuff
        clean_env["UV_NO_SYNC"] = "0"

        # point uv to the kokoro folder
        clean_env["UV_PROJECT_ENVIRONMENT"] = os.path.join(KOKORO_FOLDER, ".venv")

        disconnect_child_from_parent_process = 0

        # TODO stricter debug checks for starting process? if unlike kokoro even with duplicate processes it stops itself by checking if the port is already in use or running(in that program, not here/this one) it doesnt have a smart startup check like that

        # disconnect child process from main.py's stop signals so kokoro can stay running in debug mode even with constant main.py stops
        if config.debug:
            print("DEBUG MODE: seperating process group so kokoro persists")
            disconnect_child_from_parent_process = subprocess.CREATE_NEW_PROCESS_GROUP # use a separate process group
        else:
            print("PRODUCTION MODE: process attached normally and thus linked to normal main.py stop signals")


        # hide kokoro output from python terminal
        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL

        # stdout = None
        # stderr = None

        # launch with the isolated environment
        process = subprocess.Popen(
            START_COMMAND,
            cwd=KOKORO_FOLDER,
            env=clean_env,
            stdout=stdout,
            stderr=stderr,
            creationflags = disconnect_child_from_parent_process
        )

        # wait for it to boot and load models
        for _ in range(45): # TODO make wait/check time configurable for different performance tiers
            if is_api_running(API_HOST, API_PORT):
                print("[Kokoro API] successfully connected")
                return process
            time.sleep(1)

        # TODO these prints dont end up in this projects python due to decoupling

        print("[Kokoro API] Error: API took too long to respond")
        process.terminate()
        sys.exit(1)

    except FileNotFoundError:
        print("[Kokoro API] Error: Couldn't find Kokoro script")
        sys.exit(1)