"""Development server runner that restarts the container on file changes."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COMMAND = [sys.executable, "manage.py", "runserver", "0.0.0.0:8000", "--noreload"]
POLL_INTERVAL = float(os.environ.get("DEVSERVER_POLL_SECONDS", "1"))
WATCHED_SUFFIXES = {
    ".py",
    ".html",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".env",
    ".ini",
    ".cfg",
    ".sh",
}
IGNORED_DIR_NAMES = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    "env",
    "venv",
    "media",
    "static",
    "staticfiles",
}


def iter_files(root: Path):
    for current_root, dir_names, file_names in os.walk(root):
        dir_names[:] = [
            dir_name
            for dir_name in dir_names
            if dir_name not in IGNORED_DIR_NAMES
        ]
        current_path = Path(current_root)
        for file_name in file_names:
            path = current_path / file_name
            if path.suffix.lower() in WATCHED_SUFFIXES or path.name in {".env", "docker-compose.yml", "Dockerfile"}:
                yield path


def snapshot(root: Path) -> dict[str, int]:
    state: dict[str, int] = {}
    for path in iter_files(root):
        try:
            state[str(path.relative_to(root))] = path.stat().st_mtime_ns
        except FileNotFoundError:
            continue
    return state


def terminate_child(process: subprocess.Popen | None):
    if not process or process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    child: subprocess.Popen | None = None

    def handle_signal(signum, _frame):
        terminate_child(child)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    print("Starting development server with container restart watcher...")
    child = subprocess.Popen(COMMAND, cwd=PROJECT_ROOT)
    previous_state = snapshot(PROJECT_ROOT)

    try:
        while True:
            if child.poll() is not None:
                return child.returncode

            time.sleep(POLL_INTERVAL)
            current_state = snapshot(PROJECT_ROOT)
            if current_state != previous_state:
                print("File change detected. Stopping server so Docker can restart the container...")
                terminate_child(child)
                return 0
    finally:
        terminate_child(child)


if __name__ == "__main__":
    raise SystemExit(main())
