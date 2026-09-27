# Linux installation

Use a checkout or the repository's source ZIP. Python 3.11+ with `venv`/`ensurepip`,
or an interpreter with pip 22.3+ selected via `--python`,
a graphical Linux desktop, and internet access for Python dependencies are required.
The installer does not run sudo, change shell profiles, or alter system Python.

```sh
git clone https://github.com/sergeych/inlay.git
cd inlay
./install.sh
inlay
```

By default the application is installed in `~/.local/share/inlay/venv` (or under
`$XDG_DATA_HOME/inlay`) and its launcher in `~/.local/bin/inlay`. If that directory is
not on PATH, the installer prints the line to add to your shell configuration.
Installation uses a regular package, so it remains usable after moving or removing
the checkout. Only the editor is installed; the AI skill is installed separately.

Options:

```sh
./install.sh --prefix "$HOME/apps/inlay" --bin-dir "$HOME/bin" --python python3.12
./install.sh --help
```

An existing unrelated launcher is preserved unless you specify `--force`.
Use that flag deliberately when replacing a development launcher. Nonempty installation
directories without Inlay's marker are refused, even with `--force`.

To update, fetch the desired revision and run the installer again with the same options.
The selected Python interpreter is used when creating a new environment; to change
Python versions, choose a fresh prefix. A failed dependency installation can leave an
incomplete environment; fix the reported problem and rerun the installer.

## System libraries

Qt needs graphics and desktop libraries supplied by the operating system. On
Debian/Ubuntu, common prerequisites are:

```sh
sudo apt-get install python3-venv libegl1 libopengl0 libxkbcommon0 libnss3 libxcb-cursor0 fonts-dejavu-core libfontconfig1 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libxtst6 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0
```

ALSA is also required (`libasound2t64` on Ubuntu 24.04, `libasound2` on older releases).
Other distributions use different package names. The installer checks Qt imports;
a successful check does not replace testing an actual graphical session. It keeps
QtWebEngine's normal sandbox enabled.

## Remove

For the default paths, remove the launcher and dedicated installation directory:

```sh
rm "$HOME/.local/bin/inlay"
rm -r "${XDG_DATA_HOME:-$HOME/.local/share}/inlay"
```

Adjust these paths if you installed elsewhere. Diagram files and the source checkout
are separate and remain untouched.
