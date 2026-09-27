# Third-party notices

Our code is MIT licensed; this does not relicense bundled dependencies.

The local Mermaid 12.0.0 bundle lives in `app/src/inlay/web/`. Its license is
`MERMAID-LICENSE`; bundled dependency notices are in `mermaid.js.LEGAL.txt`.
`build-package-lock.json` records the build dependency tree. Preserve these files
with redistributed bundles. esbuild is a build tool, not a runtime requirement.

PySide6/Qt and Pillow are installed separately and retain their respective licenses.
Review their distribution requirements if building a self-contained application.
