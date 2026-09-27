import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from inlay.app import Window
from inlay.core import read_document


def test_edit_render_save_reopen_and_failure(tmp_path):
    app = QApplication.instance() or QApplication([])
    w = Window(); w.show(); app.processEvents()
    source = Path('examples/hello.py').read_text()
    w.editor.setPlainText(source); w.render()
    def wait():
        until = time.monotonic() + 15
        while w.job:
            app.processEvents(); time.sleep(.02)
            assert time.monotonic() < until
    wait()
    assert w.rendered_source == source
    out = tmp_path / 'hello.png'; w.write(out, None)
    assert read_document(out) == source
    w.open_path(out)
    changed = source.replace('Edit source', 'Change source')
    w.editor.setPlainText(changed)
    w.save(); wait()
    assert read_document(out) == changed
    before = out.read_bytes()
    w.editor.setPlainText('#!/usr/bin/env python3\nraise RuntimeError("oops")')
    w.save(); wait()
    assert out.read_bytes() == before
    assert w.rendered_source == changed
    assert 'oops' in w.log.toPlainText()
    w.editor.setPlainText(changed); w.close()
