# Using Inlay

Open an existing PNG with `bin/inlay picture.png`, or run without arguments to
create a Python diagram. New's dropdown also offers Mermaid. Import source loads
a plain source file into the editor. Save writes the rendered image and its source
together; Save As preserves the original file.

Mermaid previews update while typing. Errors retain the last successful result.
Executable sources render on request; Live can be enabled explicitly. Stop cancels
a render; scripts time out after 120 seconds. Python sources use the application's
Python environment unless their shebang selects another interpreter.

A script receives the output PNG path as its first argument. Relative inputs are
resolved from the image or imported source directory. The temporary script's
`__file__` is not that directory. Older scripts that write several hard-coded output
files need adapting to this single-output contract.

Explicit embedded source type wins over detection. For older images Inlay recognizes
Mermaid prologues, shebangs and Python syntax; select the type when detection is
ambiguous. Mermaid source is plain text, not an executable wrapper.

Saving after a source edit renders first, so saved pixels and source agree. External
file changes are checked before replacing the image. Use Save As if another program
changed the file. Executable sources run with your local permissions: inspect unfamiliar
code before rendering it.

The current export is raster PNG (Mermaid uses up to 2× resolution, capped at 8192
pixels per dimension). SVG editing/export and syntax highlighting are not implemented.
Linux is verified; other desktop platforms still need testing.
