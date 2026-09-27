"""Render, save and capture the installed GUI; run with a display or under Xvfb."""
import argparse
import tempfile
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from inlay.app import Window
from inlay.core import read_document
import inlay
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path)
args=parser.parse_args()
output=args.output_dir or Path(tempfile.mkdtemp(prefix='inlay-gui-check-'))
output.mkdir(parents=True, exist_ok=True)
if any((output/name).exists() for name in ('diagram.png', 'window.png')):
 parser.error('Choose an output directory without diagram.png or window.png')
print('Package under test:', inlay.__file__)
app=QApplication([])
w=Window(); w.show(); w.set_type('mermaid')
source='flowchart LR\n A[Installed in Incus] --> B[Live Mermaid] --> C[Editable PNG]'
w.editor.setPlainText(source)
end=time.monotonic()+45
while w.rendered_source != source:
 app.processEvents();time.sleep(.02)
 assert time.monotonic()<end,w.log.toPlainText()
out=output/'diagram.png'
w.write(out,None)
assert read_document(out)==source
end=time.monotonic()+2
while time.monotonic()<end:
 app.processEvents(); time.sleep(.02)
w.grab().save(str(output/'window.png'))
w.close()
print('PASS: live Mermaid, save and source recovery. Inspect:', output/'window.png')
