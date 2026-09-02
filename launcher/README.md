# QuantumResilientCommunication Launcher

A console-based launcher that orchestrates the development environment.

## Features

- **Docker/PostgreSQL**: Starts PostgreSQL via Docker Compose and waits for readiness
- **FastAPI Backend**: Starts the backend using the existing `backend/venv`
- **Vite Frontend**: Starts the frontend using the existing `web/node_modules`
- **Port Detection**: Detects port conflicts and warns about duplicates
- **Browser Launch**: Opens `http://127.0.0.1:5175` when the frontend is ready
- **Clean Shutdown**: Stops backend and frontend on Ctrl+C (leaves Docker/PostgreSQL running)

## Building the EXE

1. Ensure PyInstaller is installed:
   ```bash
   pip install pyinstaller
   ```

2. Run the build script:
   ```bash
   build.bat
   ```

3. The EXE will be created at:
   ```
   launcher\QuantumResilientCommunication.exe
   ```

## Usage

Double-click `QuantumResilientCommunication.exe` or run from command prompt:

```bash
QuantumResilientCommunication.exe
```

The launcher will:
1. Check Docker is running
2. Start PostgreSQL via Docker Compose
3. Start FastAPI backend on `127.0.0.1:8000`
4. Start Vite frontend on `127.0.0.1:5175`
5. Open browser to `http://127.0.0.1:5175`
6. Monitor services and report any failures

Press **Ctrl+C** to stop the launcher. Docker/PostgreSQL will remain running.

## Requirements

- Python 3.9+ (for building)
- Docker Desktop
- Node.js 18+
- Existing `backend/venv` with dependencies installed
- Existing `web/node_modules` with dependencies installed

## Notes

- The launcher does NOT bundle Python, Node.js, PostgreSQL, Docker, venv, node_modules, or project files
- Docker/PostgreSQL is left running when the launcher exits (by design)
- The launcher detects the project directory relative to its own location