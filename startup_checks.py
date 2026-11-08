"""Startup checks for the local TTS backend and its Docker service."""

import urllib.error
import urllib.request
import webbrowser
from tkinter import messagebox
from urllib.parse import urlparse

from config_handler import config


def is_kokoro_available(timeout=2):
    """Return True when the configured Kokoro API answers on its health route."""
    base = str(config.kokoro_host or "http://localhost").rstrip("/")
    if "://" not in base:
        base = f"http://{base}"

    parsed = urlparse(base)
    host = parsed.hostname or "localhost"
    try:
        port = parsed.port or int(config.kokoro_port)
    except (TypeError, ValueError):
        port = 8880
    url = f"{parsed.scheme or 'http'}://{host}:{port}/health"

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def ensure_docker_ready(docker_manager, parent=None):
    """Return 'ready', 'continue', or 'quit' after checking and prompting for Docker."""
    asked_to_start = False
    while True:
        status = docker_manager.check_docker()
        if status["ready"]:
            return "ready"

        message = docker_manager.describe_status(status)
        print(message)

        if status["reason"] == "not_installed":
            choice = messagebox.askyesnocancel(
                "Docker is not installed",
                f"{message}\n\nYes: open the download page and quit\n"
                "No: continue without Docker\nCancel: quit",
                parent=parent,
            )
            if choice is True:
                webbrowser.open("https://docs.docker.com/desktop/")
                return "quit"
            return "continue" if choice is False else "quit"

        if not status["cli_installed"]:
            choice = messagebox.askyesnocancel(
                "Docker CLI unavailable",
                f"{message}\n\nYes: open the Docker Desktop page and quit\n"
                "No: continue without Docker\nCancel: quit",
                parent=parent,
            )
            if choice is True:
                webbrowser.open("https://docs.docker.com/desktop/")
                return "quit"
            return "continue" if choice is False else "quit"

        if status["reason"] == "compose_missing":
            choice = messagebox.askyesnocancel(
                "Docker Compose required",
                f"{message}\n\nYes: open the Compose install page and quit\n"
                "No: continue without Docker\nCancel: quit",
                parent=parent,
            )
            if choice is True:
                webbrowser.open("https://docs.docker.com/compose/install/")
                return "quit"
            return "continue" if choice is False else "quit"

        if status["desktop_installed"] and status["reason"] == "not_running" and not asked_to_start:
            asked_to_start = True
            start_now = messagebox.askyesno(
                "Docker Desktop is not running",
                f"{message}\n\nStart Docker Desktop now?",
                parent=parent,
            )
            if start_now:
                print("Starting Docker Desktop and waiting for the engine...")
                if docker_manager.start_docker_desktop():
                    return "ready"
                messagebox.showerror(
                    "Docker Engine unavailable",
                    docker_manager.describe_status(),
                    parent=parent,
                )

        choice = messagebox.askyesnocancel(
            "Docker Engine not running",
            f"{message}\n\nYes: retry\nNo: continue without Docker\nCancel: quit",
            parent=parent,
        )
        if choice is None:
            return "quit"
        if choice is False:
            return "continue"


def ensure_backend_ready(docker_manager, parent=None):
    """Prepare the selected TTS backend; return False only when the user quits."""
    service_name = "kokoro-tts"

    if config.active_tts_api != "KOKORO":
        print(f"{config.active_tts_api} backend selected; the local Kokoro Docker service is not required.")
        return True

    if is_kokoro_available():
        print("Kokoro API is already reachable; skipping the Docker service.")
        return True

    docker_state = ensure_docker_ready(docker_manager, parent)
    if docker_state == "quit":
        return False
    if docker_state == "continue":
        print("Continuing without the managed Kokoro service.")
        return True

    if docker_manager.ensure_service_running(service_name):
        return True

    logs = docker_manager.get_service_logs(service_name, tail=20)
    if logs:
        print(f"Recent Kokoro logs:\n{logs}")
    messagebox.showerror(
        "Kokoro TTS unavailable",
        "Docker is running, but the Kokoro TTS service could not start.\n\n"
        "The app will stay open, but speech will fail until Kokoro is available.",
        parent=parent,
    )
    print("Continuing without a ready Kokoro service.")
    return True
