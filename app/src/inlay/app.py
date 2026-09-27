"""The small desktop editor: source, preview, render, save."""
import argparse
import base64
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import Qt, QTimer, QCoreApplication
from PySide6.QtGui import QAction, QFontDatabase, QKeySequence, QPixmap, QPainter
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel,
    QPlainTextEdit, QSplitter, QFileDialog, QMessageBox, QToolBar, QGraphicsView,
    QGraphicsScene, QComboBox, QCheckBox, QStackedWidget, QMenu)

from .core import RenderJob, read_document, save_document, fingerprint
from .source_type import detect, document_type

QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

MERMAID_TEMPLATE = 'flowchart LR\n    A[Edit source] --> B[Live preview]\n    B --> C[Save PNG with source]\n'

TEMPLATE = '''#!/usr/bin/env python3
import sys
from PIL import Image, ImageDraw

image = Image.new("RGB", (1000, 600), "white")
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((100, 150, 900, 450), radius=30, fill="#3176bd")
draw.text((500, 300), "Hello, Inlay", anchor="mm", fill="white", font_size=48)
image.save(sys.argv[1])
'''


class Preview(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)
        self.fitting = True

    def display(self, path):
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            raise ValueError('Cannot display the rendered PNG')
        self.scene().clear()
        item = self.scene().addPixmap(pixmap)
        self.scene().setSceneRect(item.boundingRect())
        self.fit()

    def fit(self):
        self.fitting = True
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fitting:
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom(self, factor):
        self.fitting = False
        self.scale(factor, factor)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(1.2 if event.angleDelta().y() > 0 else 1 / 1.2)
            event.accept()
        else:
            super().wheelEvent(event)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1360, 860)
        self.path = None
        self.expected = None
        self.cwd = Path.cwd()
        self.saved_source = ''
        self.rendered_source = None
        self.job = None
        self.pending_save = None
        self.loading = True
        self.revision = 0
        self.web = None
        self.web_request = None
        self.saved_type = 'python'
        self.rendered_type = None
        self.debounce = QTimer(self); self.debounce.setSingleShot(True)
        self.debounce.setInterval(220); self.debounce.timeout.connect(self.render)
        self.web_timeout = QTimer(self); self.web_timeout.setSingleShot(True)
        self.web_timeout.setInterval(120000); self.web_timeout.timeout.connect(self.web_timed_out)
        self.temp = tempfile.TemporaryDirectory(prefix='inlay-preview-')
        self.image_path = Path(self.temp.name) / 'preview.png'
        self.timer = QTimer(self); self.timer.setInterval(60)
        self.timer.timeout.connect(self.check_render)
        self.editor = QPlainTextEdit()
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont); font.setPointSize(11)
        self.editor.setFont(font)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setTabStopDistance(self.editor.fontMetrics().horizontalAdvance(' ') * 4)
        self.editor.textChanged.connect(self.changed)
        self.preview = Preview()
        self.previews = QStackedWidget(); self.previews.addWidget(self.preview)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(145)
        self.log.setFont(font); self.log.hide()
        split = QSplitter()
        for title, widget in [('SOURCE', self.editor), ('PREVIEW · Ctrl+wheel to zoom', self.previews)]:
            panel = QWidget(); layout = QVBoxLayout(panel)
            label = QLabel(title); label.setStyleSheet('font-weight:600; color:#61738a; padding:6px')
            layout.addWidget(label); layout.addWidget(widget)
            split.addWidget(panel)
        split.setSizes([540, 820])
        central = QWidget(); layout = QVBoxLayout(central)
        layout.addWidget(split); layout.addWidget(self.log); self.setCentralWidget(central)
        toolbar = QToolBar(); toolbar.setMovable(False); self.addToolBar(toolbar)
        self.actions = {}
        def action(name, fn, shortcut=None):
            a = QAction(name, self)
            if shortcut: a.setShortcut(QKeySequence(shortcut))
            a.triggered.connect(lambda checked=False: fn())
            toolbar.addAction(a)
            self.actions[name] = a
            return a
        new_action = action('New', self.new_document, 'Ctrl+N')
        new_menu = QMenu(self)
        new_menu.addAction('Python diagram', lambda: self.new_document('python'))
        new_menu.addAction('Mermaid diagram', lambda: self.new_document('mermaid'))
        new_action.setMenu(new_menu)
        action('Open…', self.choose_open, 'Ctrl+O')
        action('Import source…', self.import_source)
        toolbar.addSeparator()
        action('Render', self.render, 'Ctrl+Return')
        action('Stop', self.stop, 'Escape').setEnabled(False)
        toolbar.addSeparator()
        action('Save', self.save, 'Ctrl+S')
        action('Save As…', lambda: self.save(True), 'Ctrl+Shift+S')
        action('Export source…', self.export_source)
        toolbar.addSeparator()
        action('Fit', lambda: self.current_preview().fit(), 'Ctrl+0')
        action('Zoom +', lambda: self.current_preview().zoom(1.25), 'Ctrl++')
        action('Zoom −', lambda: self.current_preview().zoom(.8), 'Ctrl+-')
        toolbar.addSeparator()
        self.language = QComboBox()
        for label, value in [('Python', 'python'), ('Mermaid', 'mermaid'), ('Shell', 'shell'), ('Shebang', 'executable'), ('Unknown', 'unknown')]:
            self.language.addItem(label, value)
        self.language.setToolTip('Source type · stored in PNG metadata')
        self.language.currentIndexChanged.connect(self.language_changed)
        toolbar.addWidget(self.language)
        self.live = QCheckBox('Live'); self.live.setToolTip('Update preview after editing')
        self.live.toggled.connect(self.live_changed); toolbar.addWidget(self.live)
        self.editor.setPlainText(TEMPLATE)
        self.loading = False
        self.statusBar().showMessage('Ready · Render runs the source using its shebang')

    def source_type(self):
        return self.language.currentData()

    def current_preview(self):
        return self.previews.currentWidget()

    def set_type(self, value):
        self.language.blockSignals(True)
        self.language.setCurrentIndex(self.language.findData(value))
        self.language.blockSignals(False)
        self.live.blockSignals(True); self.live.setChecked(value == 'mermaid'); self.live.blockSignals(False)

    def language_changed(self):
        self.live.blockSignals(True); self.live.setChecked(self.source_type() == 'mermaid'); self.live.blockSignals(False)
        self.changed()

    def live_changed(self, enabled):
        if enabled and not self.loading: self.debounce.start()
        else: self.debounce.stop()

    def changed(self):
        source = self.editor.toPlainText()
        dirty = source != self.saved_source or self.source_type() != self.saved_type
        self.setWindowTitle(f'{"* " if dirty else ""}{self.path.name if self.path else "Untitled"} — Inlay')
        if self.loading: return
        self.revision += 1
        self.web_request = None; self.web_timeout.stop()
        if self.web: self.web.invalidate(self.revision)
        self.pending_save = None
        if source != self.rendered_source or self.source_type() != self.rendered_type:
            self.statusBar().showMessage('Source changed · waiting for preview' if self.live.isChecked() else 'Source changed · Render to update the preview')
            if self.live.isChecked(): self.debounce.start()
        else: self.debounce.stop()

    def error(self, e):
        self.log.setPlainText(str(e)); self.log.show()
        self.statusBar().showMessage('Failed · previous image and file preserved')

    def may_discard(self):
        if self.job:
            return False
        if self.editor.toPlainText() == self.saved_source and self.source_type() == self.saved_type:
            return True
        return QMessageBox.question(self, 'Unsaved source', 'Discard unsaved changes?',
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Discard

    def new_document(self, kind='python'):
        if not self.may_discard(): return
        self.stop(); self.loading = True
        self.path = None; self.expected = None; self.rendered_source = None; self.saved_source = ''
        self.rendered_type = None; self.saved_type = kind
        self.set_type(kind)
        self.preview.scene().clear(); self.previews.setCurrentWidget(self.preview); self.log.hide()
        self.editor.setPlainText(MERMAID_TEMPLATE if kind == 'mermaid' else TEMPLATE)
        self.loading = False; self.changed()

    def choose_open(self):
        if not self.may_discard(): return
        name, _ = QFileDialog.getOpenFileName(self, 'Open diagram', str(self.cwd), 'PNG images (*.png)')
        if name: self.open_path(name)

    def open_path(self, name):
        try:
            path = Path(name).resolve()
            source = read_document(path)
            kind = document_type(path, source)
            self.stop(); self.loading = True
            self.preview.display(path); self.previews.setCurrentWidget(self.preview)
            self.set_type(kind); self.saved_type = kind; self.rendered_type = kind
            self.image_path.write_bytes(path.read_bytes())
            self.path = path; self.cwd = path.parent; self.expected = fingerprint(path)
            self.saved_source = source; self.rendered_source = source
            self.editor.setPlainText(source); self.editor.document().setModified(False)
            self.log.hide(); self.loading = False; self.changed()
            self.statusBar().showMessage('Opened · type: ' + kind + (' · Live preview on edit' if kind == 'mermaid' else ' · Render to execute source'))
        except Exception as e: self.error(e)

    def import_source(self):
        if not self.may_discard(): return
        name, _ = QFileDialog.getOpenFileName(self, 'Import source', str(self.cwd), 'All files (*)')
        if not name: return
        try:
            source = Path(name).read_bytes().decode('utf8')
            self.stop(); self.loading = True
            self.path = None; self.expected = None; self.saved_source = ''; self.rendered_source = None
            kind = detect(source); self.set_type(kind); self.saved_type = kind; self.rendered_type = None
            self.cwd = Path(name).resolve().parent
            self.preview.scene().clear(); self.previews.setCurrentWidget(self.preview); self.log.hide(); self.editor.setPlainText(source)
            self.loading = False; self.changed()
        except Exception as e: self.error(e)

    def export_source(self):
        name, _ = QFileDialog.getSaveFileName(self, 'Export source', str(self.cwd / ('diagram.mmd' if self.source_type() == 'mermaid' else 'diagram.py')))
        if name:
            try: Path(name).write_text(self.editor.toPlainText(), encoding='utf8')
            except Exception as e: self.error(e)

    def busy(self, value):
        for name in ('New', 'Open…', 'Import source…', 'Render', 'Save', 'Save As…'):
            self.actions[name].setEnabled(not value)
        self.actions['Stop'].setEnabled(value)
        self.editor.setReadOnly(value)
        self.language.setEnabled(not value)

    def render(self):
        self.debounce.stop()
        if self.job: return
        if self.source_type() == 'mermaid':
            self.render_mermaid(); return
        try:
            self.job = RenderJob(self.editor.toPlainText(), self.cwd, source_type=self.source_type())
            self.busy(True); self.log.hide(); self.timer.start()
            self.statusBar().showMessage('Rendering… · Escape to stop')
        except Exception as e:
            self.pending_save = None; self.error(e)

    def render_mermaid(self):
        if self.web is None:
            from .mermaid_view import MermaidView
            self.web = MermaidView(); self.previews.addWidget(self.web)
            self.web.result.connect(self.mermaid_result)
        self.revision += 1
        self.web_request = (self.revision, self.editor.toPlainText())
        self.actions['Stop'].setEnabled(True)
        self.web.submit(*self.web_request); self.web_timeout.start()
        self.statusBar().showMessage('Rendering Mermaid…')

    def mermaid_result(self, revision, png, error):
        if not self.web_request or revision != self.web_request[0]: return
        source = self.web_request[1]; self.web_request = None; self.web_timeout.stop()
        self.actions['Stop'].setEnabled(False)
        if error:
            self.pending_save = None; self.error(error); return
        try:
            self.image_path.write_bytes(base64.b64decode(png.split(',', 1)[1], validate=True))
            self.rendered_source = source; self.rendered_type = 'mermaid'
            self.previews.setCurrentWidget(self.web); self.web.fit()
            self.log.hide(); self.statusBar().showMessage('Mermaid preview up to date')
            if self.pending_save:
                target, expected = self.pending_save; self.pending_save = None
                self.write(target, expected)
        except Exception as e:
            self.pending_save = None; self.error(e)

    def web_timed_out(self):
        self.stop(); self.error('Mermaid render exceeded 120 seconds')

    def check_render(self):
        try:
            if not self.job.poll(): return
            self.preview.display(self.job.output); self.previews.setCurrentWidget(self.preview)
            self.image_path.write_bytes(self.job.output.read_bytes())
            self.rendered_source = self.job.source; self.rendered_type = self.source_type()
            diagnostics = self.job.diagnostics()
            self.log.setPlainText(diagnostics); self.log.setVisible(bool(diagnostics.strip()))
            self.finish_job()
            self.statusBar().showMessage('Rendered · Save embeds this source in the PNG')
            if self.pending_save:
                target, expected = self.pending_save; self.pending_save = None
                self.write(target, expected)
        except Exception as e:
            self.finish_job(); self.pending_save = None; self.error(e)

    def finish_job(self):
        self.timer.stop()
        if self.job: self.job.close(); self.job = None
        self.busy(False)

    def stop(self):
        self.debounce.stop(); self.web_timeout.stop()
        was_rendering = self.web_request is not None
        self.revision += 1; self.web_request = None
        if self.web:
            self.web.invalidate(self.revision)
            if was_rendering:
                self.web.restart()
                if self.image_path.exists(): self.preview.display(self.image_path)
                self.previews.setCurrentWidget(self.preview)
        self.finish_job(); self.pending_save = None
        self.statusBar().showMessage('Stopped · previous preview preserved')

    def save(self, save_as=False):
        target = self.path
        if save_as or target is None:
            name, _ = QFileDialog.getSaveFileName(self, 'Save diagram', str(target or self.cwd / 'diagram.png'), 'PNG images (*.png)')
            if not name: return
            target = Path(name).resolve()
            if not target.suffix: target = target.with_suffix('.png')
        expected = self.expected if target == self.path else (fingerprint(target) if target.exists() else None)
        if self.rendered_source != self.editor.toPlainText() or self.rendered_type != self.source_type():
            self.pending_save = (target, expected); self.render()
        else:
            self.write(target, expected)

    def write(self, target, expected):
        try:
            save_document(self.image_path, self.rendered_source, target, expected, self.rendered_type)
            self.path = target; self.cwd = target.parent; self.expected = fingerprint(target)
            self.saved_source = self.rendered_source; self.saved_type = self.rendered_type; self.changed()
            self.statusBar().showMessage(f'Saved · {target}')
        except Exception as e: self.error(e)

    def closeEvent(self, event):
        if self.job:
            QMessageBox.information(self, 'Render running', 'Stop the render before closing.')
            event.ignore(); return
        if not self.may_discard(): event.ignore(); return
        self.stop(); self.temp.cleanup(); event.accept()


def main():
    p = argparse.ArgumentParser(description='Inlay — edit the source inside a PNG')
    p.add_argument('image', nargs='?')
    args = p.parse_args()
    app = QApplication(sys.argv[:1]); app.setApplicationName('Inlay')
    app.setStyle('Fusion')
    window = Window()
    if args.image: window.open_path(args.image)
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
