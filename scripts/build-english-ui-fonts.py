#!/usr/bin/env python3
"""Regenerate the English BLE experiment UI faces with the project font converter.
Run with a Python environment containing freetype-py and fonttools.
Chinese book rendering continues to use the existing SD font system.
"""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
fonts = root / "lib/EpdFont/builtinFonts"
for size, weight in ((10, "regular"), (14, "regular"), (14, "bold")):
    name = f"en_ui_{size}_{weight}"
    source = fonts / "source/Ubuntu" / f"Ubuntu-{weight.title()}.ttf"
    with (fonts / f"{name}.h").open("w") as out:
        subprocess.run([sys.executable, "lib/EpdFont/scripts/fontconvert.py",
                        name, str(size), str(source.relative_to(root))], cwd=root, stdout=out, check=True)
