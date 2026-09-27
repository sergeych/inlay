# Native Inlay diagrams for LibreOffice Writer

The extension adds a real **Inlay Diagram** embedded object, with its own source,
language and preview stored inside the ODT. A replacement image lets people without
the extension view and print the document. Editing requires Inlay and this extension.

## Install

Install the desktop editor with the repository's `./install.sh`. Then close LibreOffice
normally and run:

```sh
./integrations/libreoffice/install.sh
```

Alternatively, build with `python3 tools/build_libreoffice.py` and add
`dist/inlay-writer-0.1.0.oxt` through **Tools → Extensions**. Reopen LibreOffice afterward.
The extension needs LibreOffice's Python scripting support (on distributions that split
it into packages, install `libreoffice-script-provider-python`). It does not need Qt
inside the LibreOffice process. Linux is the initially supported platform.

## Use

The **Inlay** menu in Writer provides:

- **Insert diagram…** — insert a new object and open Inlay.
- **Edit diagram** — edit the selected Inlay object; native object activation also opens it.
- **Import Inlay PNG…** — turn a source-bearing PNG into a native diagram object.
- **Export Inlay PNG…** — save a portable PNG with editable source.

Save in Inlay to update the object in Writer. Each successful update is an undoable
operation. The surrounding document remains unsaved until you save it yourself.
Closing Inlay without saving makes no update. Save As creates an independent file;
it does not retarget the Writer object. Keep the object's existing frame size while
editing; resizing in Writer remains available.

If the object is removed, its document closes, or another edit/Undo changes it before
a new editor save, updates stop. The message gives the recovery PNG path; errors and
editor output are retained beside it. An editor crash also retains the working files.
Opening an ODT only displays the cached preview; it does not execute diagram code.

Editor discovery checks `~/.local/bin/inlay`, `~/bin/inlay`, then PATH. To override it,
put one absolute executable path in `~/.config/inlay/libreoffice-editor` (no arguments
or shell syntax). This also supports a wrapper script for local configuration.

## Format and boundaries

Each object has class ID `A3299102-761D-48D5-A881-784269D7D480` and storage media type
`application/vnd.inlay.diagram`. Its ODT substorage contains `source.txt`, `preview.png`
and `diagram.json`; the preview and source must agree. See [the architecture decision](../../docs/adr/0002-writer-extension.md).

The first version supports Writer and ODT. DOCX conversion and Calc/Impress editing
are not qualified. No source reconstruction is attempted for ordinary PNG pictures.
The extension does not replace arbitrary image objects or modify the user's office
security settings. Without the extension the object can be displayed and preserved,
but cannot be edited as an Inlay diagram.

## Verified baseline

LibreOffice 26.2.5.2 on Linux: the packaged OXT was installed into isolated profiles
and tested with the actual Inlay renderer. Checks cover the menu command, automatic
updates, Undo/Redo, independent copy/paste, cancellation, stale-editor conflict
protection, process restart and recipient resaving without the extension. PDF output
with and without the extension matched pixel-for-pixel. The Writer window and menu
were also visually inspected under a private X display.

Run `/usr/bin/python3 tools/check_libreoffice.py` from the repository root to repeat
the integration checks; the interpreter needs UNO, and `.venv` needs the editor.
