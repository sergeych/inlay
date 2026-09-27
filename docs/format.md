# Source-bearing PNG, version 1

A normal PNG carries editable UTF-8 source in textual metadata. Pixels remain
readable by standard image viewers. Metadata may occur after IDAT, so readers must
scan through IEND rather than inspect only the header.

| Field | Meaning |
| --- | --- |
| `Source` | Complete source text, written as UTF-8 iTXt |
| `SourceType` | `python`, `mermaid`, `shell`, `executable`, or `unknown` |
| `SourceManifest` | JSON with `version: 1`, `sha256`, and `source_type` |

The SHA-256 covers the exact UTF-8 source bytes, including newlines. It detects
mismatch, not authorship. Writers may include descriptive `filename`,
`render_command` and `requirements`; these do not authorize execution or install
dependencies. A source file with external inputs is not a self-contained diagram.

Readers accept legacy tEXt/zTXt source and images without a manifest. Type selection
uses SourceType, then manifest source_type, then legacy SourceLanguage, then source
detection. Explicit `unknown` is retained rather than overridden by guessing.

Executable source has a shebang and writes one PNG to argv[1]; recognized Python
can omit the shebang. Execution takes place in the image/import directory, while the
script itself is temporary. Mermaid source is ordinary Mermaid text.

The editor saves only a successful rendering paired with the exact source used to
produce it, replaces files atomically and checks for external modifications. The
standalone helper creates new files exclusively, refuses signed dSIG PNGs, preserves
other PNG chunks and verifies source recovery. Keep a source sidecar too: some image
processing and document pipelines remove metadata.

This version describes PNG only. No SVG metadata or office completion protocol is
specified here.
