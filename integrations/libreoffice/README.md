# LibreOffice integration — planned

There is no installable extension or `.oxt` yet.

Intended Writer workflow:

1. Select an embedded source-bearing PNG.
2. Extract it to a temporary working file and open it in Inlay.
3. After a successful save, update the same graphic object, preserving its anchor
   and size. Make the document change undoable.
4. Cancellation or rendering failure leaves the document untouched.

Reuse Inlay's editor and PNG metadata contract rather than embed another renderer.
Before implementing, settle the save/completion protocol, application discovery,
concurrent document edits, closed documents, temporary file cleanup and metadata
preservation through Writer. Test both actual document behavior and packaged extension
installation. No transport or callback API is committed by this draft.
