"""Mở game Flashcard tiếng Trung.

Chạy: python3 run.py  (hoặc bấm Run trong VS Code)
Lần đầu chạy, nếu máy chưa có pygame, script tự tạo môi trường .venv và cài pygame-ce.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
VENV_PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def has_pygame(python=sys.executable):
    return subprocess.run([str(python), "-c", "import pygame"], capture_output=True).returncode == 0


def ensure_pygame():
    try:
        import pygame  # noqa: F401
        return
    except ImportError:
        pass
    in_venv = Path(sys.prefix).resolve() == VENV.resolve()
    if not in_venv:
        if not VENV_PY.exists():
            print("Đang tạo môi trường .venv ...")
            subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
        if not has_pygame(VENV_PY):
            print("Đang cài pygame-ce (chỉ lần đầu) ...")
            subprocess.check_call([str(VENV_PY), "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")])
        # chạy lại chính file này bằng Python trong .venv
        os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve())])
    print("Đang cài pygame-ce (chỉ lần đầu) ...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")])


if __name__ == "__main__":
    ensure_pygame()
    sys.path.insert(0, str(ROOT))
    from game.main import main
    main()
