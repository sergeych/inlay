# Development

From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ./app pytest build
QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu .venv/bin/python -m pytest -q
python3 tools/sync_skill.py --check
python3 tools/build_skill.py
.venv/bin/python -m build app --outdir dist
```

Inspect the actual editor for UI changes as well as running tests. Keep existing
user windows and unsaved work intact. Launch from outside the checkout too when
changing packaging or path handling.

After changing `app/src/inlay/png.py`, run `python3 tools/sync_skill.py` and include
the copied helper in the same change. The portable skill archive contains its
instructions, helper and license; it needs no installed application.

Mermaid rebuilding instructions and the exact npm dependency lock are in
`app/src/inlay/web/BUILD.md`. Node is a build dependency only. Preserve bundled
license notices when updating the renderer.

GitHub Actions runs tests and builds distributions; it does not publish a release.
Do not package local environments, private continuity notes or IDE configuration.
The root LICENSE is authoritative; keep app/LICENSE and skills/inlay/LICENSE in sync.
