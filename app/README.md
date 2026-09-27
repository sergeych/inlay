# Inlay desktop editor

Edit the source embedded in a PNG and preview the result. Supports executable
sources and live Mermaid through a bundled local QtWebEngine renderer.

From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ./app
bin/inlay examples/trust.png
```

See the repository README and docs/usage.md for behavior and limitations.
Bundled Mermaid licenses are included alongside its JavaScript in `inlay/web/`.

Authors: sergeych and Codex (OpenAI), AI collaborator.
