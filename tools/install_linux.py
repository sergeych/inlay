#!/usr/bin/env python3
"""Install Inlay for the current Linux user, without modifying system Python."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'Inlay user installation v1\n'


def install(args):
    if not sys.platform.startswith('linux'):
        raise ValueError('This installer currently supports Linux only.')
    prefix = Path(args.prefix).expanduser().resolve()
    bin_dir = Path(args.bin_dir).expanduser().resolve()
    launcher = bin_dir / 'inlay'
    venv = prefix / 'venv'
    marker = prefix / '.inlay-install'
    command = '#!/bin/sh\n# Installed by Inlay\nexec ' + shlex.quote(str(venv / 'bin/python')) + ' -m inlay.app "$@"\n'
    if launcher.exists() or launcher.is_symlink():
        if not args.force and (launcher.is_symlink() or not launcher.is_file() or launcher.read_text() != command):
            raise ValueError(f'{launcher} already exists. Choose --bin-dir or use --force to replace it.')
        if launcher.is_dir():
            raise ValueError(f'{launcher} is a directory; refusing to replace it.')
    if prefix.exists() and any(prefix.iterdir()) and (not marker.is_file() or marker.read_text() != MARKER):
        raise ValueError(f'{prefix} is not an Inlay installation. Choose an empty --prefix.')
    subprocess.run([args.python, '-c',
                    'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'], check=True)
    if not (ROOT / 'app/pyproject.toml').is_file():
        raise ValueError('Run install.sh from a complete Inlay checkout or source archive.')
    prefix.mkdir(parents=True, exist_ok=True)
    marker.write_text(MARKER)
    has_ensurepip = subprocess.run([args.python, '-c', 'import ensurepip'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not (venv / 'bin/python').exists():
        subprocess.run([args.python, '-m', 'venv', '--without-pip', str(venv)], check=True)
    has_pip = subprocess.run([str(venv / 'bin/python'), '-m', 'pip', '--version'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not has_pip:
        if has_ensurepip:
            subprocess.run([str(venv / 'bin/python'), '-m', 'ensurepip', '--upgrade'], check=True)
        else:
            # A recent pip can bootstrap a separate environment without touching its host.
            has_host_pip = subprocess.run([args.python, '-m', 'pip', '--version'],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
            if not has_host_pip:
                raise ValueError('Install Python venv/ensurepip support (Debian/Ubuntu: python3-venv), '
                                 'or select --python with pip 22.3+ available, then retry.')
            subprocess.run([args.python, '-m', 'pip', '--python', str(venv / 'bin/python'),
                            'install', 'pip'], check=True)
    subprocess.run([str(venv / 'bin/python'), '-m', 'pip', 'install', '--upgrade', str(ROOT / 'app')], check=True)
    # Import Qt before replacing the launcher, so missing shared libraries are reported here.
    subprocess.run([str(venv / 'bin/python'), '-c',
                    'from PySide6 import QtWidgets, QtWebEngineWidgets; import inlay.app'], check=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.inlay-', dir=bin_dir)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(command)
        os.chmod(temporary, 0o755)
        os.replace(temporary, launcher)
    finally:
        Path(temporary).unlink(missing_ok=True)
    print(f'Installed Inlay: {launcher}\nEnvironment: {venv}')
    path_dirs = {Path(p).expanduser().resolve() for p in os.environ.get('PATH', '').split(os.pathsep) if p}
    if bin_dir not in path_dirs:
        print('Add this line to your shell configuration:\n  export PATH=' + shlex.quote(str(bin_dir)) + ':"$PATH"')
    print('Run: ' + shlex.quote(str(launcher)) + '\nSee docs/install-linux.md for system libraries and removal.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    data_home = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    parser.add_argument('--prefix', default=str(data_home / 'inlay'), help='installation directory')
    parser.add_argument('--bin-dir', default=str(Path.home() / '.local/bin'), help='launcher directory')
    parser.add_argument('--python', default=sys.executable, help='Python 3.11+ interpreter for a new environment')
    parser.add_argument('--force', action='store_true', help='replace an existing launcher at the selected destination')
    args = parser.parse_args()
    try:
        install(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Installation failed: {error}\nSee docs/install-linux.md for prerequisites and recovery.\n')


if __name__ == '__main__':
    main()
