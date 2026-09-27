"""Exercise the actual bundled Mermaid in Qt WebEngine, not a mock renderer."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
from PySide6.QtWidgets import QApplication
from inlay.app import Window
from inlay.core import read_document
from inlay.source_type import document_type


def test_live_mermaid_errors_latest_revision_save_reopen(tmp_path):
    app=QApplication.instance() or QApplication([])
    w=Window();w.show();w.set_type('mermaid')
    def until(check):
        deadline=time.monotonic()+30
        while not check():
            app.processEvents();time.sleep(.02)
            assert time.monotonic()<deadline, w.log.toPlainText()
    source='flowchart LR\n A[Hello] --> B[World]'
    w.editor.setPlainText(source)
    until(lambda:w.rendered_source==source)
    out=tmp_path/'diagram.png';w.write(out,None)
    assert document_type(out,read_document(out))=='mermaid'
    previous=out.read_bytes()
    # An invalid intermediate edit retains the last successful picture.
    w.editor.setPlainText('flowchart LR\n A[')
    until(lambda:not w.log.isHidden())
    assert w.rendered_source==source and out.read_bytes()==previous
    # Save while an update is pending must commit exactly the latest source.
    changed='sequenceDiagram\n Alice->>Bob: Привет!'
    w.editor.setPlainText(changed);w.save()
    until(lambda:w.saved_source==changed)
    assert read_document(out)==changed
    old=w.revision
    newest='flowchart TD\n X --> Y --> Z'
    w.editor.setPlainText(newest)
    w.mermaid_result(old,'','obsolete error')
    until(lambda:w.rendered_source==newest)
    assert w.log.isHidden()
    w.write(out,w.expected);w.open_path(out)
    assert w.source_type()=='mermaid' and w.editor.toPlainText()==newest
    w.grab().save(str(tmp_path/'mermaid-window.png'))
    w.close()
