#!/usr/bin/env python3
"""Synchronize the standalone metadata helper from the application."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    source = ROOT / 'app/src/inlay/png.py'
    target = ROOT / 'skills/inlay/scripts/png_source.py'
    if args.check:
        if not target.exists() or source.read_bytes() != target.read_bytes():
            parser.exit(1, 'Skill helper differs; run tools/sync_skill.py\n')
    else:
        target.write_bytes(source.read_bytes())
    print('Skill helper is synchronized')

if __name__ == '__main__':
    main()
