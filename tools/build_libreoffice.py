#!/usr/bin/env python3
"""Build the Writer extension with the canonical standard-library PNG helper."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    output = ROOT / 'dist/inlay-writer-0.1.0.oxt'
    output.parent.mkdir(exist_ok=True)
    source = ROOT / 'integrations/libreoffice/extension'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                archive.write(path, path.relative_to(source))
        archive.write(ROOT / 'app/src/inlay/png.py', 'pythonpath/inlay_png.py')
        archive.write(ROOT / 'LICENSE', 'LICENSE')
    print(output)

if __name__ == '__main__': main()
