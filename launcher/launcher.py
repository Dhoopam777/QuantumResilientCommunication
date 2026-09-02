#!/usr/bin/env python3
"""
QuantumResilientCommunication Launcher
========================================
A console-based launcher that orchestrates the development environment:
- PostgreSQL via Docker Compose
- FastAPI backend via existing venv
- Vite frontend via existing node_modules

Usage:
    QuantumResilientCommunication.exe

The launcher will:
1. Detect the project directory relative to the EXE
2. Check Docker Desktop/engine
3. Start PostgreSQL Docker service
4. Wait until PostgreSQL is ready
5. Start FastAPI backend using existing venv
6. Start Vite frontend using existing node_modules
7. Detect/avoid duplicate services
8. Detect port conflicts and show useful errors
9. Open http://localhost:127.0.0.1:5175 in browser when ready
10. Keep running while services are running
11. Clean shutdown of child processes on Ctrl+C

Docker/PostgreSQL is left running when the launcher exits.
"""

import os
import sys
import time
import socket
import subprocess
import signal
import platform
import urllib.request
import urllib.error

# --- Configuration ---
PROJECT_ROOT = None
BACKEND_DIR = None
WEB_DIR = None
DOCKER_COMPOSE_DIR = None
VENV_PYTHON = None
VENV_ACTIVATE = None
BACKEND_PORT = 8000
FRONTEND_PORT = 5175
POSTGRES_PORT = 5432
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}"
DOCKER_COMPOSE_FILE = "docker-compose.yml"
DOCKER_CONTAINER_NAME = "quantum-resilient-db"

# Track child processes for cleanup
child_processes = []


def get_project_root():
    """Detect the project directory relative to the EXE or script."""
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        exe_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        exe_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Project root is the parent of the launcher directory
    project_root = os.path.dirname(exe_dir)
    return project_root


def check_docker():
    """Check if Docker Desktop/engine is running."""
    print("[LAUNCHER] Checking Docker...")
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("[LAUNCHER] Docker is running.")
            return True
        else:
            print("[LAUNCHER] ERROR: Docker is not running.")
            print("[LAUNCHER] Please start Docker Desktop and try again.")
            return False
    except FileNotFoundError:
        print("[LAUNCHER] ERROR: Docker is not installed or not in PATH.")
        return False
    except subprocess.TimeoutExpired:
        print("[LAUNCHER] ERROR: Docker check timed out.")
        return False


def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def check_port_conflicts():
    """Check for port conflicts and return a list of conflicts."""
    conflicts = []
    
    if is_port_in_use(POSTGRES_PORT):
        conflicts.append(f"PostgreSQL port {POSTGRES_PORT} is already in use")
    if is_port_in_use(BACKEND_PORT):
        conflicts.append(f"Backend port {BACKEND_PORT} is already in use")
    if is_port_in_use(FRONTEND_PORT):
        conflicts.append(f"Frontend port {FRONTEND_PORT} is already in use")
    
    return conflicts


def start_postgres():
    """Start PostgreSQL via Docker Compose."""
    print("[LAUNCHER] Starting PostgreSQL via Docker Compose...")
    
    compose_file = os.path.join(DOCKER_COMPOSE_DIR, DOCKER_COMPOSE_FILE)
    if not os.path.exists(compose_file):
        print(f"[LAUNCHER] ERROR: Docker Compose file not found: {compose_file}")
        return False
    
    try:
        result = subprocess.run(
            ["docker-compose", "up", "-d"],
            cwd=DOCKER_COMPOSE_DIR,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("[LAUNCHER] PostgreSQL container started.")
            return True
        else:
            print(f"[LAUNCHER] ERROR: Failed to start PostgreSQL:")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("[LAUNCHER] ERROR: docker-compose is not installed or not in PATH.")
        return False
    except subprocess.TimeoutExpired:
        print("[LAUNCHER] ERROR: Docker Compose start timed out.")
        return False


def wait_for_postgres():
    """Wait until PostgreSQL is ready."""
    print("[LAUNCHER] Waiting for PostgreSQL to be ready...")
    
    max_attempts = 30
    for attempt in range(1, max_attempts + 1):
        try:
            result = subprocess.run(
                ["docker", "exec", DOCKER_CONTAINER_NAME, "pg_isready", "-U", "user", "-d", "quantum_resilient_db"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("[LAUNCHER] PostgreSQL is ready.")
                return True
        except subprocess.TimeoutExpired:
            pass
        
        print(f"[LAUNCHER] Waiting for PostgreSQL... (attempt {attempt}/{max_attempts})")
        time.sleep(2)
    
    print("[LAUNCHER] ERROR: PostgreSQL did not become ready in time.")
    return False


def start_backend():
    """Start FastAPI backend using existing venv."""
    print("[LAUNCHER] Starting FastAPI backend...")
    
    if not os.path.exists(VENV_PYTHON):
        print(f"[LAUNCHER] ERROR: venv Python not found: {VENV_PYTHON}")
        return False
    
    try:
        # Start the backend process
        proc = subprocess.Popen(
            [VENV_PYTHON, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT), "--reload"],
            cwd=BACKEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0
        )
        
        child_processes.append(("backend", proc))
        print(f"[LAUNCHER] Backend started (PID: {proc.pid}).")
        return True
    except Exception as e:
        print(f"[LAUNCHER] ERROR: Failed to start backend: {e}")
        return False


def wait_for_backend():
    """Wait until the backend is ready."""
    print("[LAUNCHER] Waiting for backend to be ready...")
    
    max_attempts = 30
    for attempt in range(1, max_attempts + 1):
        try:
            url = f"{BACKEND_URL}/health"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    print("[LAUNCHER] Backend is ready.")
                    return True
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError):
            pass
        
        print(f"[LAUNCHER] Waiting for backend... (attempt {attempt}/{max_attempts})")
        time.sleep(2)
    
    print("[LAUNCHER] ERROR: Backend did not become ready in time.")
    return False


def find_npx():
    """Find the npx executable."""
    # Check in web/node_modules/.bin
    if platform.system() == "Windows":
        # On Windows, use npx.cmd (not npx which is a shell script)
        npx_local = os.path.join(WEB_DIR, "node_modules", ".bin", "npx.cmd")
        if os.path.exists(npx_local):
            return npx_local
        # Also check for npx.cmd in system PATH
        try:
            result = subprocess.run(
                ["where", "npx.cmd"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except:
            pass
    else:
        npx_local = os.path.join(WEB_DIR, "node_modules", ".bin", "npx")
        if os.path.exists(npx_local):
            return npx_local
        try:
            result = subprocess.run(
                ["which", "npx"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except:
            pass
    
    return None


def start_frontend():
    """Start Vite frontend using existing node_modules."""
    print("[LAUNCHER] Starting Vite frontend...")
    
    # Check if node_modules exists
    node_modules = os.path.join(WEB_DIR, "node_modules")
    if not os.path.exists(node_modules):
        print(f"[LAUNCHER] ERROR: node_modules not found: {node_modules}")
        print("[LAUNCHER] Please run 'npm install' in the web directory first.")
        return False
    
    # Find npx
    npx_path = find_npx()
    if not npx_path:
        print("[LAUNCHER] ERROR: npx is not installed or not in PATH.")
        print("[LAUNCHER] Please install Node.js and try again.")
        return False
    
    print(f"[LAUNCHER] Using npx: {npx_path}")
    
    try:
        # Use npx to run vite
        proc = subprocess.Popen(
            [npx_path, "vite", "--host", "127.0.0.1", "--port", str(FRONTEND_PORT)],
            cwd=WEB_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0
        )
        
        child_processes.append(("frontend", proc))
        print(f"[LAUNCHER] Frontend started (PID: {proc.pid}).")
        return True
    except FileNotFoundError:
        print("[LAUNCHER] ERROR: npx is not installed or not in PATH.")
        print("[LAUNCHER] Please install Node.js and try again.")
        return False
    except Exception as e:
        print(f"[LAUNCHER] ERROR: Failed to start frontend: {e}")
        return False


def wait_for_frontend():
    """Wait until the frontend is ready."""
    print("[LAUNCHER] Waiting for frontend to be ready...")
    
    max_attempts = 30
    for attempt in range(1, max_attempts + 1):
        try:
            url = FRONTEND_URL
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    print("[LAUNCHER] Frontend is ready.")
                    return True
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError):
            pass
        
        print(f"[LAUNCHER] Waiting for frontend... (attempt {attempt}/{max_attempts})")
        time.sleep(2)
    
    print("[LAUNCHER] ERROR: Frontend did not become ready in time.")
    return False


def open_browser():
    """Open the browser to the frontend URL."""
    print(f"[LAUNCHER] Opening browser at {FRONTEND_URL}...")
    try:
        import webbrowser
        webbrowser.open(FRONTEND_URL)
        print("[LAUNCHER] Browser opened.")
    except Exception as e:
        print(f"[LAUNCHER] WARNING: Could not open browser: {e}")
        print(f"[LAUNCHER] Please open {FRONTEND_URL} manually.")


def cleanup():
    """Clean up child processes on exit."""
    print("\n[LAUNCHER] Shutting down child processes...")
    
    for name, proc in child_processes:
        try:
            if proc.poll() is None:
                print(f"[LAUNCHER] Stopping {name} (PID: {proc.pid})...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"[LAUNCHER] Force killing {name} (PID: {proc.pid})...")
                    proc.kill()
                    proc.wait(timeout=5)
                print(f"[LAUNCHER] {name} stopped.")
        except Exception as e:
            print(f"[LAUNCHER] WARNING: Error stopping {name}: {e}")
    
    print("[LAUNCHER] Child processes stopped.")
    print("[LAUNCHER] Docker/PostgreSQL left running (as requested).")


def signal_handler(signum, frame):
    """Handle Ctrl+C signal."""
    print("\n[LAUNCHER] Received interrupt signal.")
    cleanup()
    sys.exit(0)


def main():
    """Main launcher entry point."""
    global PROJECT_ROOT, BACKEND_DIR, WEB_DIR, DOCKER_COMPOSE_DIR, VENV_PYTHON, VENV_ACTIVATE
    
    print("=" * 60)
    print("QuantumResilientCommunication Launcher")
    print("=" * 60)
    print()
    
    # Set up signal handler for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Detect project directory
    PROJECT_ROOT = get_project_root()
    BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
    WEB_DIR = os.path.join(PROJECT_ROOT, "web")
    DOCKER_COMPOSE_DIR = BACKEND_DIR
    
    # Set venv Python path
    if platform.system() == "Windows":
        VENV_PYTHON = os.path.join(BACKEND_DIR, "venv", "Scripts", "python.exe")
    else:
        VENV_PYTHON = os.path.join(BACKEND_DIR, "venv", "bin", "python")
    
    print(f"[LAUNCHER] Project root: {PROJECT_ROOT}")
    print(f"[LAUNCHER] Backend dir: {BACKEND_DIR}")
    print(f"[LAUNCHER] Web dir: {WEB_DIR}")
    print(f"[LAUNCHER] venv Python: {VENV_PYTHON}")
    print()
    
    # Check Docker
    if not check_docker():
        sys.exit(1)
    
    # Check for port conflicts
    conflicts = check_port_conflicts()
    if conflicts:
        print("[LAUNCHER] WARNING: Port conflicts detected:")
        for conflict in conflicts:
            print(f"  - {conflict}")
        print("[LAUNCHER] The launcher will attempt to start services anyway.")
        print()
    
    # Start PostgreSQL
    if not start_postgres():
        sys.exit(1)
    
    # Wait for PostgreSQL
    if not wait_for_postgres():
        sys.exit(1)
    
    # Start backend
    if not start_backend():
        sys.exit(1)
    
    # Wait for backend
    if not wait_for_backend():
        cleanup()
        sys.exit(1)
    
    # Start frontend
    if not start_frontend():
        cleanup()
        sys.exit(1)
    
    # Wait for frontend
    if not wait_for_frontend():
        cleanup()
        sys.exit(1)
    
    # Open browser
    open_browser()
    
    print()
    print("=" * 60)
    print("All services started successfully!")
    print(f"Frontend: {FRONTEND_URL}")
    print(f"Backend: {BACKEND_URL}")
    print(f"PostgreSQL: localhost:{POSTGRES_PORT}")
    print()
    print("Press Ctrl+C to stop the launcher (Docker/PostgreSQL will remain running).")
    print("=" * 60)
    
    # Keep running and monitor child processes
    try:
        while True:
            # Check if any child process has died
            for name, proc in child_processes:
                if proc.poll() is not None:
                    print(f"[LAUNCHER] WARNING: {name} process exited unexpectedly (code: {proc.returncode}).")
                    # Read any remaining output
                    try:
                        output, _ = proc.communicate(timeout=1)
                        if output:
                            print(f"[LAUNCHER] {name} output:\n{output}")
                    except:
                        pass
                    print("[LAUNCHER] Press Ctrl+C to exit.")
                    # Remove from list so we don't keep reporting it
                    child_processes.remove((name, proc))
                    break
            
            if not child_processes:
                print("[LAUNCHER] All child processes have exited.")
                break
            
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()