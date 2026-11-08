"""Manage Compose services and inspect their containers through the Docker SDK."""

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

import docker

logger = logging.getLogger(__name__)

COMPOSE_FILE = Path(__file__).resolve().with_name("docker.compose.yml")
COMPOSE_PROJECT = "fresh-ai-tts"


class DockerManager:
    """Start Compose services and inspect their containers using Docker labels."""

    def __init__(self, compose_file=COMPOSE_FILE, project_name=COMPOSE_PROJECT,
                 compose_environment=None, client=None):
        self.compose_file = Path(compose_file)
        self.project_name = project_name
        self.compose_environment = dict(compose_environment or {})
        self._client = client
        self._owns_client = client is None
        self.last_error = None

    def _get_client(self, log_errors=True):
        try:
            if self._client is None:
                self._client = docker.from_env(timeout=5)
            self._client.ping()
            self.last_error = None
            return self._client
        except docker.errors.DockerException as error:
            if log_errors:
                logger.warning("Docker Engine unavailable: %s", error)
            self.last_error = str(error)
            if self._client is not None and self._owns_client:
                self._client.close()
            self._client = None
            return None

    def is_engine_running(self, quiet=False):
        """Return True when the Docker API responds to a ping."""
        return self._get_client(log_errors=not quiet) is not None

    def _docker_cli_path(self):
        """Return the docker CLI path, including a Docker Desktop fallback."""
        docker_cli = shutil.which("docker")
        if docker_cli:
            return Path(docker_cli)

        desktop_path = self._docker_desktop_path()
        if desktop_path is not None:
            candidate = desktop_path.parent / "resources" / "bin" / "docker.exe"
            if candidate.is_file():
                return candidate
        return None

    def _compose_status(self, docker_cli):
        """Return (available, version, error) for the Compose v2 plugin."""
        try:
            result = subprocess.run(
                [docker_cli, "compose", "version", "--short"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return False, None, str(error)

        version = result.stdout.strip() or None
        if result.returncode == 0:
            return True, version, None
        error = (result.stderr or result.stdout).strip() or f"exit code {result.returncode}"
        return False, None, error

    @staticmethod
    def _docker_desktop_path(docker_cli=None):
        """Return the Docker Desktop executable path when it is installed."""
        if os.name != "nt":
            return None

        candidates = []
        program_files = os.environ.get("ProgramFiles")
        if program_files:
            candidates.append(Path(program_files) / "Docker" / "Docker" / "Docker Desktop.exe")
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(Path(local_app_data) / "Programs" / "DockerDesktop" / "Docker Desktop.exe")
            candidates.append(Path(local_app_data) / "Docker" / "Docker Desktop.exe")
        if docker_cli:
            cli_path = Path(docker_cli)
            candidates.append(cli_path.parent.parent.parent / "Docker Desktop.exe")
            candidates.append(cli_path.parent / "Docker Desktop.exe")

        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _classify_engine_error(error):
        text = (error or "").lower()
        if any(marker in text for marker in (
            "cannot connect",
            "error during connect",
            "createfile",
            "cannot find the file",
            "is the docker daemon running",
            "connection refused",
            "no such file",
        )):
            return "not_running"
        if "permission denied" in text or "access is denied" in text:
            return "permission"
        return "error"

    def check_docker(self):
        """Report whether Docker, Compose, and the engine are usable."""
        docker_cli = self._docker_cli_path()
        docker_cli_text = str(docker_cli) if docker_cli else None
        compose_installed, compose_version, compose_error = (
            self._compose_status(docker_cli_text) if docker_cli_text else (False, None, None)
        )
        engine_running = self.is_engine_running()
        desktop_path = self._docker_desktop_path(docker_cli_text)

        if docker_cli is None:
            reason = "cli_missing" if desktop_path is not None else "not_installed"
        elif not engine_running:
            reason = self._classify_engine_error(self.last_error)
        elif not compose_installed:
            reason = "compose_missing"
        else:
            reason = "ready"

        return {
            "sdk_installed": True,
            "cli_installed": docker_cli is not None,
            "compose_installed": compose_installed,
            "engine_running": engine_running,
            "desktop_installed": desktop_path is not None,
            "desktop_path": str(desktop_path) if desktop_path else None,
            "ready": reason == "ready",
            "reason": reason,
            "error": self.last_error or compose_error,
            "compose_version": compose_version,
            "docker_path": docker_cli_text,
        }

    def describe_status(self, status=None):
        """Return an actionable explanation for a check_docker result."""
        status = status or self.check_docker()
        reason = status["reason"]
        if reason == "ready":
            return "Docker is ready."
        if reason == "not_installed":
            return (
                "Docker is not installed. Install Docker Desktop, or install Docker Engine "
                "with the Compose plugin, from https://docs.docker.com/desktop/ and start it."
            )
        if reason == "cli_missing":
            return (
                "Docker Desktop appears to be installed, but the docker CLI could not be found. "
                "Repair or reinstall Docker Desktop so 'docker' is available."
            )
        if reason == "compose_missing":
            return (
                "Docker Compose v2 is not available. Update Docker Desktop or install "
                "the compose plugin, then confirm 'docker compose version' works."
            )
        if reason == "not_running":
            if status["desktop_installed"]:
                return "Docker Desktop is installed but its engine is not running. Start Docker Desktop and retry."
            return "The Docker engine is not running. Start Docker Desktop or the Docker service, then retry."
        if reason == "permission":
            return "Docker Engine denied access. Check Docker Desktop permissions or your docker group membership."
        return f"Docker Engine could not be reached: {status['error'] or 'unknown error'}"

    def start_docker_desktop(self, timeout=120, poll_interval=2):
        """Launch Docker Desktop on Windows and wait for the engine to respond."""
        desktop_path = self._docker_desktop_path(self._docker_cli_path())
        if desktop_path is None:
            return False

        try:
            subprocess.Popen(
                [str(desktop_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as error:
            logger.error("Could not start Docker Desktop: %s", error)
            return False

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_engine_running(quiet=True):
                return True
            time.sleep(poll_interval)
        logger.error("Docker Desktop did not become ready within %s seconds", timeout)
        return False

    def _get_service_container(self, client, service_name):
        containers = client.containers.list(
            all=True,
            filters={
                "label": [
                    f"com.docker.compose.project={self.project_name}",
                    f"com.docker.compose.service={service_name}",
                ]
            },
        )
        if not containers:
            return None
        return next((item for item in containers if item.status == "running"), containers[0])

    def get_service_status(self, service_name):
        """Return Docker availability and state for one Compose service."""
        client = self._get_client()
        if client is None:
            return {"available": False, "installed": False, "state": "unavailable", "health": None}

        try:
            container = self._get_service_container(client, service_name)
            if container is None:
                return {"available": True, "installed": False, "state": "missing", "health": None}

            container.reload()
            state = container.attrs.get("State", {})
            return {
                "available": True,
                "installed": True,
                "state": state.get("Status", container.status),
                "health": state.get("Health", {}).get("Status"),
                "container_id": container.short_id,
                "name": container.name,
                "exit_code": state.get("ExitCode"),
                "error": state.get("Error") or None,
            }
        except docker.errors.DockerException as error:
            logger.warning("Failed to inspect Compose service %s: %s", service_name, error)
            return {"available": False, "installed": False, "state": "unavailable", "health": None}

    def get_service_logs(self, service_name, tail=100):
        """Return recent logs for a service container, or None if unavailable."""
        client = self._get_client()
        if client is None:
            return None

        try:
            container = self._get_service_container(client, service_name)
            if container is None:
                return None
            return container.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
        except docker.errors.DockerException as error:
            logger.warning("Failed to read logs for Compose service %s: %s", service_name, error)
            return None

    def _run_compose(self, *arguments, timeout=600):
        if not self.compose_file.is_file():
            logger.error("Docker Compose file not found: %s", self.compose_file)
            return False

        docker_cli = self._docker_cli_path()
        if docker_cli is None:
            logger.error("Docker CLI is not installed or is not on PATH")
            return False

        command = [
            str(docker_cli),
            "compose",
            "--project-name",
            self.project_name,
            "-f",
            str(self.compose_file),
            *arguments,
        ]
        environment = os.environ.copy()
        environment.update(self.compose_environment)

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=environment,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            logger.error("Failed to run Docker Compose: %s", error)
            return False

        output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        if result.returncode:
            logger.error("Docker Compose command failed: %s", output or result.returncode)
            return False
        if output:
            logger.info("%s", output)
        return True

    def install_service(self, service_name, timeout=600):
        """Pull an image and start the named Compose service."""
        return self._run_compose("pull", service_name, timeout=timeout) and self._run_compose(
            "up", "-d", service_name, timeout=timeout
        )

    def start_service(self, service_name):
        """Start or create the named Compose service without pulling its image."""
        return self._run_compose("up", "-d", service_name)

    def stop_service(self, service_name):
        """Stop the named Compose service without removing its container."""
        return self._run_compose("stop", service_name)

    def restart_service(self, service_name):
        """Restart the named Compose service without pulling its image."""
        return self._run_compose("restart", service_name)

    def wait_for_service(self, service_name, timeout=60, poll_interval=1):
        """Wait until the service is running and its Docker healthcheck passes."""
        deadline = time.monotonic() + timeout
        while True:
            status = self.get_service_status(service_name)
            if not status["available"]:
                return False

            if status["installed"]:
                if status["state"] in {"exited", "dead", "removing"}:
                    logger.error("Compose service %s stopped: %s", service_name, status)
                    logs = self.get_service_logs(service_name, tail=30)
                    if logs:
                        logger.error("Recent %s logs:\n%s", service_name, logs)
                    return False
                if status["state"] == "running" and status["health"] in (None, "healthy"):
                    return True

            if time.monotonic() >= deadline:
                logger.error("Timed out waiting for Compose service %s: %s", service_name, status)
                return False
            time.sleep(poll_interval)

    def ensure_service_running(self, service_name, timeout=60):
        """Start a service if needed and wait for it to become healthy."""
        status = self.get_service_status(service_name)
        if not status["available"]:
            logger.error("%s", self.describe_status())
            return False

        if status["state"] != "running":
            logger.info("Starting Compose service %s", service_name)
            if not self.start_service(service_name):
                return False

        return self.wait_for_service(service_name, timeout=timeout)

    def close(self):
        """Close the SDK client when this manager created it."""
        if self._client is not None and self._owns_client:
            self._client.close()
            self._client = None
