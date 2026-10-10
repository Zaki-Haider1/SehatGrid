"""Run the two application processes behind one same-origin public endpoint."""

import os
import signal
import subprocess
import sys
import time

subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"], cwd="/app/backend", check=True
)
api = subprocess.Popen(
    [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ],
    cwd="/app/backend",
)
web = subprocess.Popen(
    ["node", "server.js"],
    cwd="/app/frontend",
    env={**os.environ, "HOSTNAME": "0.0.0.0", "PORT": os.environ.get("PORT", "3000")},
)


def stop(*_):
    for child in [web, api]:
        if child.poll() is None:
            child.terminate()
    for child in [web, api]:
        try:
            child.wait(timeout=8)
        except subprocess.TimeoutExpired:
            child.kill()


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
while api.poll() is None and web.poll() is None:
    time.sleep(0.5)
stop()
sys.exit(api.returncode or web.returncode or 0)
