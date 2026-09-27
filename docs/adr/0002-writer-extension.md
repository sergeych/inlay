# 0002: Native embedded Inlay diagrams in Writer

Status: accepted, 2026-09-28. Supersedes the unshipped image-editing prototype.

The user chose a real diagram object rather than editing arbitrary Writer pictures.
Use Writer TextEmbeddedObject with a dedicated Inlay class ID and UNO embedded-object
factory. Source text, its language, presentation settings and preview are stored in
that object's own ODT substorage. The preview is also supplied as Writer's replacement
graphic so recipients without the extension can view and print the document.

Activation opens the separate Inlay editor; successful saves update the object through
LibreOffice's event queue. Do not execute diagram code merely by opening the document.
Keep the portable source-bearing PNG as an interchange format for the editor and
imports/exports, not as the only source of truth inside the document.

First gate: real insertion, save/reopen, independent copies and visible fallback without
the extension. Then editing, Undo and failure handling. Verify in isolated profiles;
do not install into or modify a user's active office profile while proving the design.

Official references: XEmbeddedObject, XEmbedPersist, XVisualObject and
XEmbedObjectCreator at https://api.libreoffice.org/docs/idl/ref/ .
