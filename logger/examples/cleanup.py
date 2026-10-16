"""Makefile's portable, cross-platform clean target."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
count = 0
for path in root.rglob("__pycache__"):
    if path.is_dir():
        shutil.rmtree(path)
        count += 1
for path in [root / "examples" / "output", root / "build", root / "dist"]:
    if path.exists():
        shutil.rmtree(path)
        count += 1
for path in root.glob("*.egg-info"):
    shutil.rmtree(path)
    count += 1
print(f"[CLEAN] Removed {count} generated directories")
