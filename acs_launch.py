#!/usr/bin/env python
"""
ACS Unified Launcher (CNC Prod 2G)
Starts the Django web API server and orchestrates background workers.
"""

import os
import sys
import time
import subprocess
import signal

# Ensure paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ACS_DIR = os.path.join(ROOT_DIR, "acs")
DOT_VENV_PYTHON = os.path.join(ROOT_DIR, ".venv", "Scripts", "python.exe") if sys.platform == "win32" else os.path.join(ROOT_DIR, ".venv", "bin", "python")
VENV_PYTHON = os.path.join(ROOT_DIR, "venv", "Scripts", "python.exe") if sys.platform == "win32" else os.path.join(ROOT_DIR, "venv", "bin", "python")

if os.path.exists(DOT_VENV_PYTHON):
    PYTHON_EXEC = DOT_VENV_PYTHON
elif os.path.exists(VENV_PYTHON):
    PYTHON_EXEC = VENV_PYTHON
else:
    PYTHON_EXEC = sys.executable

WORKER_SCRIPTS = [
    os.path.join(ACS_DIR, "workers", "acs_order_master.py"),
    os.path.join(ACS_DIR, "workers", "acs_supply_request_pairing.py"),
    os.path.join(ACS_DIR, "workers", "acs_aligo_sync.py"),
    os.path.join(ACS_DIR, "workers", "acs_order_send.py"),
    os.path.join(ACS_DIR, "workers", "acs_telemetry_sync.py"),
    os.path.join(ACS_DIR, "workers", "acs_log_formatter.py"),
]


def main():
    print("================================================================")
    print("   ACS BACKEND - AMR FLEET CONTROL SYSTEM (VDA 5050 v2.1.0)   ")
    print("   Operational Area: CNC Prod 2G | Target: EMQX Broker        ")
    print("================================================================")

    # 1. Apply database migrations
    print("\n[Launcher] Step 1/3: Checking database migrations...")
    subprocess.run([PYTHON_EXEC, os.path.join(ROOT_DIR, "manage.py"), "migrate", "--noinput"], cwd=ROOT_DIR)

    # 2. Start Django Web Server
    print("\n[Launcher] Step 2/3: Starting Django HTTP/REST API Server on port 8000...")
    web_cmd = [PYTHON_EXEC, os.path.join(ROOT_DIR, "manage.py"), "runserver", "0.0.0.0:8000"]
    web_process = subprocess.Popen(web_cmd, cwd=ROOT_DIR)

    # 3. Start Background Workers
    print("\n[Launcher] Step 3/3: Spawning background workers...")
    worker_processes = []
    for script in WORKER_SCRIPTS:
        worker_name = os.path.basename(script)
        if os.path.exists(script):
            print(f"  -> Launching worker: {worker_name}")
            p = subprocess.Popen([PYTHON_EXEC, script], cwd=ACS_DIR)
            worker_processes.append((worker_name, p))
        else:
            print(f"  [!] Worker script missing: {script}")

    print("\n[Launcher] System successfully launched!")
    print("   - Web Dashboard:     http://localhost:8000/")
    print("   - OpenAPI / Swagger: http://localhost:8000/api/docs/")
    print("   - Django Admin:      http://localhost:8000/admin/")
    print("Press Ctrl+C to gracefully stop all processes.\n")

    def shutdown(signum=None, frame=None):
        print("\n[Launcher] Shutting down all ACS processes gracefully...")
        for name, p in worker_processes:
            print(f"  Stopping worker {name}...")
            p.terminate()
        web_process.terminate()
        for _, p in worker_processes:
            p.wait(timeout=5)
        web_process.wait(timeout=5)
        print("[Launcher] All processes terminated. Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, shutdown)
    else:
        signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1)
            # Check if web process died
            if web_process.poll() is not None:
                print("[Launcher] Web server terminated unexpectedly.")
                break
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
