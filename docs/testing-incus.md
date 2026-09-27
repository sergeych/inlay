# Testing installation in Incus

Use a separate unprivileged Ubuntu 24.04 container. Attach a working managed bridge
and storage pool from your Incus installation; no host directories or GUI sockets
need to be mounted. A virtual X server is sufficient for the GUI check.

Example creation (replace POOL and BRIDGE with local names):

```sh
incus launch images:ubuntu/24.04 inlay-install-test --no-profiles --storage POOL --network BRIDGE -c limits.cpu=2 -c limits.memory=3GiB
incus exec inlay-install-test -- apt-get update
incus exec inlay-install-test -- apt-get install -y python3-venv libegl1 libopengl0 libxkbcommon0 libnss3 libxcb-cursor0 libasound2t64 fonts-dejavu-core libfontconfig1 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libxtst6 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 xvfb xauth
incus exec inlay-install-test -- useradd --create-home --shell /bin/bash tester
```

Copy a public source archive into `/home/tester`, extract it, and assign ownership to
`tester`. Exclude local environments, private notes, credentials and IDE files.
Run `./install.sh` as `tester`, not root. Verify the installed command from outside
the checkout and render a Mermaid diagram using the installed Python environment:

```sh
incus exec inlay-install-test -- su - tester -c 'cd inlay && ./install.sh'
incus exec inlay-install-test -- su - tester -c '~/.local/bin/inlay --help'
```

For automated GUI checks, use `QT_QPA_PLATFORM=offscreen` with `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu`
and the installed `~/.local/share/inlay/venv/bin/python`. Do not disable Chromium's
sandbox to conceal a container configuration failure. Check a live render, save,
source recovery and a captured window. Stop the test container when finished; keep
it available for subsequent checks.

## Verified on 2026-09-28

Ubuntu 24.04, Python 3.12, ordinary user, default installation paths: installation,
retry after missing system libraries, launcher outside checkout, live Mermaid rendering,
PNG save and exact embedded source recovery passed. The installed package was used,
not the source tree. Qt offscreen mode ran with Chromium sandbox enabled.

Xvfb startup did not complete during this check; a normal X11/Wayland desktop session
inside this container remains unverified. The host GUI was also opened independently.
