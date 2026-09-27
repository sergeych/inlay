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

For clean Linux installation and sandboxed GUI checks, see [Incus testing](testing-incus.md).

## Writer extension

Build with `python3 tools/build_libreoffice.py`. No extra runtime dependency is added
to the editor. The extension bundles the canonical PNG helper during packaging.

Run the packaged integration check using a Python that provides UNO:

```sh
/usr/bin/python3 tools/check_libreoffice.py --editor-python "$PWD/.venv/bin/python"
```

It installs only into fresh temporary profiles, launches its own office instances,
and checks native activation with real Inlay rendering, Undo/Redo, independent
copy/paste, process restart, and lossless viewing/resaving without the extension.
It prints an artifact directory with ODT/PDF files and a JSON report. Inspect the
PDFs visually. Existing user profiles and documents are not used.

Release external UNO clipboard transferables before closing their documents. Holding
one through office shutdown reproduced an abort even with built-in Math objects on
LibreOffice 26.2.5.2. The integration check explicitly releases it and checks process
exit codes; a passing save/reopen assertion alone is insufficient.
