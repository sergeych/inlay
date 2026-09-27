# Working on Inlay

Read README.md and docs/development.md. The accepted layout is described in
[ADR 0001](docs/adr/0001-suite-layout.md).

- English UI and CLI; one toolbar with a New dropdown.
- Preserve embedded source and exact source/result correspondence. Retain sidecars.
- Explicit source type takes precedence over detection; support legacy PNGs.
- Scripts write one PNG to argv[1]; plain Mermaid needs no wrapper.
- Keep Mermaid's persistent local renderer, live preview and obsolete-result protection.
- Preserve external-change checks and the last good preview on errors.
- Inspect the actual GUI for UI changes. Never close a user's unsaved editor.
- app/src/inlay/png.py is canonical; synchronize the portable helper with tools/sync_skill.py.
- Run tests from the repository root. Do not publish without user authorization.

Optional local continuity and reflection notes under docs/ are ignored by Git.
Keep personal context out of distributable documentation and examples.
