# 0001: One repository, independently usable components

Status: accepted, 2026-09-27.

The editor, AI skill and future office integration share a source-bearing image
format. Keep them in one repository so format changes can be reviewed together.
They do not require a common runtime or a simultaneous release.

- `app/src/inlay/`: desktop application and canonical PNG metadata helper.
- `app/tests/`: editor tests; `tests/`: component interoperability tests.
- `skills/inlay/`: self-contained skill with a standard-library-only helper.
- `integrations/libreoffice/`: integration plan until implementation starts.
- `docs/`, `examples/`, `tools/`: shared format, examples and release tooling.

`tools/sync_skill.py` copies the canonical metadata helper into the skill.
CI checks that they agree. The skill can be installed without Qt or the editor.
Keep the root launcher and development virtual environment; install with
`pip install -e ./app`. Personal continuity notes remain local and ignored.

The office extension will reuse the editor and PNG contract. Its transport and
completion protocol remain open decisions; this layout does not implement them.
