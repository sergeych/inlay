#!/usr/bin/env python3
"""Build an independently installable skill archive."""
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    subprocess.run([sys.executable, str(ROOT / 'tools/sync_skill.py'), '--check'], check=True)
    output = ROOT / 'dist/inlay-skill.zip'
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in ('SKILL.md', 'LICENSE', 'scripts/png_source.py'):
            archive.write(ROOT / 'skills/inlay' / name, 'inlay/' + name)
    print(output)

if __name__ == '__main__':
    main()
