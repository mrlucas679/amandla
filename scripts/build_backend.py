"""Build the AMANDLA backend into a distributable executable.

Uses PyInstaller to bundle the FastAPI backend, all services, SASL
transformer, HARPS model, and data files into a one-folder package
that can be shipped alongside the Electron app.

Requirements:
  pip install pyinstaller>=6.0

Usage:
  python scripts/build_backend.py

Output:
  dist/amandla-backend/   — folder containing the executable + dependencies
"""

import os
import sys
import shutil
import subprocess
import time

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist", "amandla-backend")
BOOT_SCRIPT = os.path.join(PROJECT_ROOT, "backend", "boot.py")

# ── Hidden imports that PyInstaller cannot detect automatically ──────────────
# These modules are loaded dynamically (lazy imports inside functions) so
# PyInstaller's static analysis misses them.
HIDDEN_IMPORTS = [
    # Uvicorn internals needed for programmatic startup
    "uvicorn.logging",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    # Backend routers (registered in main.py via include_router)
    "backend.routers.health",
    "backend.routers.speech",
    "backend.routers.rights",
    # Backend WebSocket modules (lazy-imported in handler.py)
    "backend.ws.handler",
    "backend.ws.helpers",
    "backend.ws.session",
    # Backend services (lazy-imported in handler functions)
    "backend.services.sasl_pipeline",
    "backend.services.sign_reconstruction",
    "backend.services.sign_maps",
    "backend.services.whisper_service",
    "backend.services.ollama_service",
    "backend.services.ollama_client",
    "backend.services.ollama_pool",
    "backend.services.history_db",
    "backend.services.claude_service",
    "backend.services.nvidia_service",
    "backend.services.harps_recognizer",
    "backend.services.mediapipe_bridge",
    "backend.services.sign_buffer",
    "backend.services.gemini_service",
    # Backend shared state and middleware
    "backend.shared",
    "backend.middleware",
    # SASL transformer (imported dynamically in sasl_pipeline.py)
    "sasl_transformer",
    "sasl_transformer.transformer",
    "sasl_transformer.routes",
    "sasl_transformer.config",
    "sasl_transformer.grammar_rules",
    "sasl_transformer.models",
    "sasl_transformer.sign_library",
    "sasl_transformer.websocket_handler",
    # FastAPI / Starlette internals needed at runtime
    "multipart",
    "multipart.multipart",
    # Dotenv
    "dotenv",
    # Async file I/O
    "aiofiles",
    "aiofiles.os",
    "aiofiles.ospath",
]

# ── Data files to include in the bundle ──────────────────────────────────────
# Format: (source_path, destination_folder_in_bundle)
DATA_FILES = [
    (os.path.join(PROJECT_ROOT, "data", "sign_library.json"), "data"),
    (os.path.join(PROJECT_ROOT, ".env.example"), "."),
]

# ── Directories to copy into the bundle (HARPS model checkpoint) ─────────────
COPY_DIRS = [
    (os.path.join(PROJECT_ROOT, "backend", "harps_model"), os.path.join("backend", "harps_model")),
]


def _check_pyinstaller():
    """Verify PyInstaller is installed. Exits with an error if not found."""
    try:
        import PyInstaller  # noqa: F401
        print(f"✓ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("ERROR: PyInstaller is required.")
        print("  Install with:  pip install pyinstaller>=6.0")
        sys.exit(1)


def _build_pyinstaller_args():
    """Build the PyInstaller command-line arguments list.

    Returns:
        list of command-line argument strings.
    """
    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", "amandla-backend",
        "--noconfirm",
        "--clean",
        # One-folder mode (one-file is too slow to unpack for torch/whisper)
        "--onedir",
        # Set the working directory for imports
        "--paths", PROJECT_ROOT,
    ]

    # Hidden imports
    for module in HIDDEN_IMPORTS:
        args.extend(["--hidden-import", module])

    # Data files
    separator = ";" if sys.platform == "win32" else ":"
    for src, dest in DATA_FILES:
        if os.path.exists(src):
            args.extend(["--add-data", f"{src}{separator}{dest}"])
        else:
            print(f"  ⚠ Data file not found, skipping: {src}")

    # Collect all submodules from key packages
    for package in ["backend", "sasl_transformer"]:
        args.extend(["--collect-submodules", package])

    # Output directory
    args.extend(["--distpath", os.path.join(PROJECT_ROOT, "dist")])
    args.extend(["--workpath", os.path.join(PROJECT_ROOT, "build", "pyinstaller")])
    args.extend(["--specpath", PROJECT_ROOT])

    # Entry point
    args.append(BOOT_SCRIPT)

    return args


def _copy_extra_dirs():
    """Copy additional directories (e.g. HARPS model) into the dist bundle."""
    for src_dir, dest_rel in COPY_DIRS:
        dest_dir = os.path.join(DIST_DIR, dest_rel)
        if os.path.isdir(src_dir):
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)
            shutil.copytree(src_dir, dest_dir)
            print(f"  ✓ Copied {src_dir} → {dest_dir}")
        else:
            print(f"  ⚠ Directory not found, skipping: {src_dir}")


def _copy_env_template():
    """Copy .env.example into the dist bundle as a configuration template.

    SECURITY: Never copy the real .env — it may contain secrets.
    """
    src = os.path.join(PROJECT_ROOT, ".env.example")
    dest = os.path.join(DIST_DIR, ".env.example")
    if os.path.exists(src):
        shutil.copy2(src, dest)
        print(f"  ✓ Copied .env.example → {dest}")


def _print_summary():
    """Print build summary with file count and total size."""
    if not os.path.isdir(DIST_DIR):
        print("\n✗ Build output not found — PyInstaller may have failed.")
        return

    total_size = 0
    file_count = 0
    for root, _dirs, files in os.walk(DIST_DIR):
        for f in files:
            fp = os.path.join(root, f)
            total_size += os.path.getsize(fp)
            file_count += 1

    size_mb = total_size / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print(f"BUILD COMPLETE")
    print(f"  Output:  {DIST_DIR}")
    print(f"  Files:   {file_count}")
    print(f"  Size:    {size_mb:.1f} MB")
    print(f"{'=' * 60}")

    # Check for the executable
    exe_name = "amandla-backend.exe" if sys.platform == "win32" else "amandla-backend"
    exe_path = os.path.join(DIST_DIR, exe_name)
    if os.path.exists(exe_path):
        print(f"  ✓ Executable: {exe_path}")
    else:
        print(f"  ✗ Executable not found at {exe_path}")

    print(f"\nTo test:  cd dist/amandla-backend && ./{exe_name}")
    print(f"Then:     curl http://localhost:8000/health")


def main():
    """Run the full PyInstaller build pipeline."""
    print("=" * 60)
    print("AMANDLA Backend Build (PyInstaller)")
    print("=" * 60)

    _check_pyinstaller()

    # Build arguments
    args = _build_pyinstaller_args()
    print(f"\n[1/4] Running PyInstaller...")
    print(f"  Entry point: {BOOT_SCRIPT}")
    print(f"  Hidden imports: {len(HIDDEN_IMPORTS)}")
    print(f"  Data files: {len(DATA_FILES)}")

    start_time = time.time()
    result = subprocess.run(args, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print(f"\n✗ PyInstaller failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    elapsed = time.time() - start_time
    print(f"\n[2/4] PyInstaller finished in {elapsed:.0f}s")

    # Copy extra directories
    print("\n[3/4] Copying extra files...")
    _copy_extra_dirs()
    _copy_env_template()

    # Ensure data directory exists in the bundle
    data_dir = os.path.join(DIST_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    print(f"  ✓ Ensured {data_dir} exists")

    # Summary
    print("\n[4/4] Build summary")
    _print_summary()


if __name__ == "__main__":
    main()

