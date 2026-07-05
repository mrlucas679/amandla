"""AMANDLA backend boot entry point for PyInstaller bundled builds.

This file is the target that PyInstaller freezes into an executable.
It runs uvicorn programmatically (no --reload) and handles the frozen
environment path setup needed for packaged builds.

NOT used during development — dev mode uses `python -m uvicorn backend.main:app`.

Usage (after PyInstaller build):
  ./dist/amandla-backend/amandla-backend.exe
"""

import multiprocessing
import os
import sys


def _setup_frozen_paths():
    """Set up sys.path for frozen (PyInstaller) executables.

    PyInstaller extracts files to a temp directory (_MEIPASS).
    We need to add both the extraction root and the original
    working directory to sys.path so imports resolve correctly.
    """
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle
        bundle_dir = sys._MEIPASS  # type: ignore[attr-defined]
        # Also look in the directory containing the executable
        exe_dir = os.path.dirname(sys.executable)
    else:
        # Running as a normal Python script
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
        exe_dir = bundle_dir

    # Ensure both directories are on sys.path
    for path_dir in (bundle_dir, exe_dir):
        if path_dir not in sys.path:
            sys.path.insert(0, path_dir)

    # Set the working directory to the exe location so .env and data/ are found
    os.chdir(exe_dir)


def _get_host_and_port():
    """Read host and port from environment variables with safe defaults.

    Returns:
        Tuple of (host: str, port: int).
    """
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    try:
        port = int(os.getenv("BACKEND_PORT", "8000"))
    except ValueError:
        port = 8000
    return host, port


def main():
    """Start the AMANDLA FastAPI backend via uvicorn.

    Called as the main entry point for both frozen and unfrozen execution.
    Uses uvicorn.run() programmatically — no subprocess or shell needed.
    """
    _setup_frozen_paths()

    # Load .env before importing the app (mirrors what backend/main.py does)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not available — rely on real env vars

    host, port = _get_host_and_port()

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        log_level="info",
        # No --reload in production builds
    )


if __name__ == "__main__":
    # Required for Windows frozen executables that use multiprocessing
    multiprocessing.freeze_support()
    main()

