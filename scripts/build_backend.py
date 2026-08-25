import os
import subprocess
import sys
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_TAURI_BINARIES = os.path.join(ROOT_DIR, "src-tauri", "binaries")
TARGET_TRIPLE = "aarch64-apple-darwin"
BINARY_NAME = f"integral-signal-backend-{TARGET_TRIPLE}"

def build():
    os.makedirs(SRC_TAURI_BINARIES, exist_ok=True)
    cache_dir = os.path.join(ROOT_DIR, "build", "pyinstaller_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    env = os.environ.copy()
    env["PYINSTALLER_CONFIG_DIR"] = cache_dir
    
    venv_pyinstaller = os.path.join(ROOT_DIR, ".venv", "bin", "pyinstaller")
    if not os.path.exists(venv_pyinstaller):
        venv_pyinstaller = "pyinstaller"

    cmd = [
        venv_pyinstaller,
        "--noconfirm",
        "--clean",
        "--onefile",
        "--target-arch", "arm64",
        "--name", BINARY_NAME,
        "--distpath", SRC_TAURI_BINARIES,
        "--workpath", os.path.join(ROOT_DIR, "build", "pyinstaller"),
        "--specpath", os.path.join(ROOT_DIR, "build"),
        "--paths", os.path.join(ROOT_DIR, "backend"),
        "--paths", ROOT_DIR,
        "--collect-all", "uvicorn",
        "--collect-all", "fastapi",
        "--collect-all", "starlette",
        "--collect-all", "pydantic",
        "--collect-all", "pydantic_core",
        "--collect-all", "requests",
        "--collect-all", "bs4",
        "--collect-all", "anyio",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.loops.asyncio",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.protocols.http.httptools_impl",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.protocols.websockets.websockets_impl",
        "--hidden-import", "uvicorn.protocols.websockets.wsproto_impl",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "uvicorn.lifespan.off",
        "--hidden-import", "backend.snapshot",
        "--hidden-import", "backend.storage",
        "--hidden-import", "snapshot",
        "--hidden-import", "storage",
        os.path.join(ROOT_DIR, "backend", "main.py")
    ]
    
    print(f"Building PyInstaller backend for {TARGET_TRIPLE}...")
    subprocess.check_call(cmd, cwd=ROOT_DIR, env=env)
    
    out_binary = os.path.join(SRC_TAURI_BINARIES, BINARY_NAME)
    if os.path.exists(out_binary):
        print(f"Successfully generated: {out_binary}")
    else:
        print(f"Error: Expected binary not found at {out_binary}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    build()
