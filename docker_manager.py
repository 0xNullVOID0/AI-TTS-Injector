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

    def _get_client(self):
        try:
            if self._client is None:
                self._client = docker.from_env(timeout=5)
            self._client.ping()
            return self._client
        except docker.errors.DockerException as error:
            logger.warning("Docker Engine unavailable: %s", error)
            if self._client is not None and self._owns_client:
                self._client.close()
            self._client = None
            return None

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

        docker_cli = shutil.which("docker")
        if docker_cli is None:
            logger.error("Docker CLI is not installed or is not on PATH")
            return False

        command = [
            docker_cli,
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
