#!/usr/bin/env python3
"""Test the packaged Writer extension in private profiles. Requires Python with UNO."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
import uno

ROOT = Path(__file__).resolve().parents[1]
CLASS_ID = 'A3299102-761D-48D5-A881-784269D7D480'
SOURCE = 'flowchart LR\n A[Native diagram] --> B[Edited in Inlay]'


def prop(name, value):
    p = uno.createUnoStruct('com.sun.star.beans.PropertyValue')
    p.Name, p.Value = name, value
    return p


def wait(check, seconds=40):
    end = time.monotonic() + seconds
    while not check():
        if time.monotonic() >= end:
            raise AssertionError('Timed out waiting for office/editor')
        time.sleep(.1)


class Office:
    def __init__(self, root, home):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.profile = root / 'profile'
        self.home = home
        self.env = dict(os.environ, HOME=str(home), QT_QPA_PLATFORM='offscreen',
                        QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu')
        self.process = None
        self.desktop = None
        self.pipe = 'inlay_check_' + uuid.uuid4().hex

    def install(self, extension):
        subprocess.run(['unopkg', 'add', '-f', '-env:UserInstallation=' + self.profile.as_uri(),
                        str(extension)], env=self.env, check=True, timeout=60)

    def start(self):
        self.log = open(self.root / 'office.log', 'ab')
        self.process = subprocess.Popen(['libreoffice', '-env:UserInstallation=' + self.profile.as_uri(),
            '--headless', '--norestore', '--nodefault',
            '--accept=pipe,name=' + self.pipe + ';urp;StarOffice.ServiceManager'],
            env=self.env, stdout=self.log, stderr=self.log, start_new_session=True)
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', local)
        def connect():
            try:
                self.ctx = resolver.resolve('uno:pipe,name=' + self.pipe + ';urp;StarOffice.ComponentContext')
                return True
            except Exception:
                if self.process.poll() is not None:
                    raise RuntimeError('Test office exited; see ' + str(self.root / 'office.log'))
                return False
        wait(connect)
        self.desktop = self.ctx.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop', self.ctx)
        return self

    def document(self, path=None):
        return self.desktop.loadComponentFromURL(path.as_uri() if path else 'private:factory/swriter',
                                                '_blank', 0, (prop('Hidden', True),))

    def close(self, strict=False):
        if self.desktop is not None:
            try:
                docs = self.desktop.Components.createEnumeration()
                while docs.hasMoreElements():
                    doc = docs.nextElement()
                    if hasattr(doc, 'setModified'): doc.setModified(False)
                    if hasattr(doc, 'close'): doc.close(True)
                self.desktop.terminate()
            except Exception: pass
        if self.process is not None:
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=5)
            self.log.close()
            if strict and self.process.returncode != 0:
                raise AssertionError(f'Test office exited with {self.process.returncode}; see {self.root / "office.log"}')
        self.process = None
        self.desktop = None


def insert(doc):
    obj = doc.createInstance('com.sun.star.text.TextEmbeddedObject')
    obj.CLSID = CLASS_ID
    obj.AnchorType = uno.Enum('com.sun.star.text.TextContentAnchorType', 'AS_CHARACTER')
    doc.Text.insertTextContent(doc.Text.End, obj, False)
    assert doc.EmbeddedObjects.Count >= 1
    return obj


def embedded(obj):
    return obj.getExtendedControlOverEmbeddedObject()


def png(component):
    return bytes(component.getPropertyValue('PNG'))


def save(doc, path):
    doc.storeAsURL(path.as_uri(), (prop('FilterName', 'writer8'), prop('Overwrite', True)))


def export_pdf(doc, path):
    doc.storeToURL(path.as_uri(), (prop('FilterName', 'writer_pdf_Export'), prop('Overwrite', True)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--editor-python', type=Path, default=ROOT / '.venv/bin/python')
    p.add_argument('--output-dir', type=Path)
    args = p.parse_args()
    target = (args.output_dir or Path(tempfile.mkdtemp(prefix='inlay-office-check-'))).resolve()
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()): p.error('Use an empty output directory')
    editor_python = args.editor_python.expanduser().absolute()
    subprocess.run([str(editor_python), '-c', 'import inlay.app'], check=True)
    subprocess.run([sys.executable, str(ROOT / 'tools/build_libreoffice.py')], check=True)
    home = target / 'home'; (home / '.config/inlay').mkdir(parents=True)
    editor = target / 'editor'
    editor.write_text('#!' + str(editor_python) + '\n' + '''import sys,time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from inlay.app import Window
app=QApplication([]);w=Window();w.open_path(Path(sys.argv[1]));w.show();w.set_type('mermaid')
source=''' + repr(SOURCE) + '''
w.editor.setPlainText(source)
end=time.monotonic()+25
while w.rendered_source!=source:
 app.processEvents();time.sleep(.02)
 assert time.monotonic()<end,w.log.toPlainText()
w.write(Path(sys.argv[1]),w.expected);w.close()
''')
    editor.chmod(0o755)
    (home / '.config/inlay/libreoffice-editor').write_text(str(editor))
    installed = Office(target / 'installed', home)
    fallback = Office(target / 'without-extension', home)
    report = []
    try:
        installed.install(ROOT / 'dist/inlay-writer-0.1.0.oxt')
        installed.start()
        doc = installed.document()
        url = uno.createUnoStruct('com.sun.star.util.URL')
        url.Complete = 'org.inlay.writer:insert'; url.Protocol = 'org.inlay.writer:'; url.Path = 'insert'
        dispatch = doc.CurrentController.Frame.queryDispatch(url, '', 0)
        assert dispatch is not None, 'Writer menu protocol not registered'
        dispatch.dispatch(url, ())
        assert doc.EmbeddedObjects.Count == 1
        obj = doc.EmbeddedObjects.getByIndex(0); native = embedded(obj); component = native.getComponent()
        original = png(component); size = obj.Size; anchor = obj.AnchorType
        wait(lambda: component.getPropertyValue('Source') == SOURCE)
        manager = doc.getUndoManager()
        wait(lambda: manager.getCurrentUndoActionTitle() == 'Edit Inlay diagram')
        assert obj.Size == size and obj.AnchorType == anchor
        edited = png(component)
        manager.undo(); assert png(component) == original
        manager.redo(); assert png(component) == edited
        report.append('real editor activation, auto-update, size/anchor preservation, Undo/Redo')
        doc.CurrentController.select(obj)
        transferable = doc.CurrentController.getTransferable()
        copy_doc = installed.document()
        copy_doc.CurrentController.insertTransferable(transferable)
        # Release the external clipboard proxy before closing either office document.
        transferable = None
        copy = embedded(copy_doc.EmbeddedObjects.getByIndex(0)).getComponent()
        assert png(copy) == edited
        assert copy.getPropertyValue('ObjectIdentity') != component.getPropertyValue('ObjectIdentity')
        copy.setPropertyValue('PNG', uno.ByteSequence(original))
        assert png(component) == edited
        report.append('independent copy/paste between Writer documents')
        # Wait until the first editor session cleans up before opening a new one.
        # A second activation during an active session intentionally does nothing.
        time.sleep(1)
        ready = target / 'editor-session.txt'
        editor.write_text('#!/usr/bin/env python3\nfrom pathlib import Path\nimport sys\n' +
                          'Path(' + repr(str(ready)) + ').write_text(sys.argv[1])\n')
        previous_title = manager.getCurrentUndoActionTitle()
        native.doVerb(0)
        wait(ready.exists)
        working = Path(ready.read_text())
        wait(lambda: not working.parent.exists())
        assert png(component) == edited and manager.getCurrentUndoActionTitle() == previous_title
        report.append('closing editor without save leaves the object and Undo history intact')
        ready.unlink()
        gate = target / 'allow-editor-save'
        replacement = target / 'editor-result.png'; replacement.write_bytes(edited)
        editor.write_text('#!/usr/bin/env python3\nfrom pathlib import Path\nimport sys,time,os\n' +
            'Path(' + repr(str(ready)) + ').write_text(sys.argv[1])\n' +
            'while not Path(' + repr(str(gate)) + ').exists(): time.sleep(.05)\n' +
            'p=Path(sys.argv[1]); tmp=p.with_suffix(".new")\n' +
            'tmp.write_bytes(Path(' + repr(str(replacement)) + ').read_bytes()); os.replace(tmp,p)\n')
        native.doVerb(0); wait(ready.exists)
        working = Path(ready.read_text())
        manager.undo(); assert png(component) == original
        # This save must differ from the editor's starting PNG, as a real edit would.
        replacement.write_bytes((ROOT / 'examples/hello.png').read_bytes())
        gate.touch()
        wait(lambda: (working.parent / 'error.log').exists())
        assert png(component) == original, 'A stale editor overwrote Writer Undo'
        assert working.read_bytes() == replacement.read_bytes(), 'Recovery PNG was not retained'
        assert 'changed in Writer' in (working.parent / 'error.log').read_text()
        manager.redo(); assert png(component) == edited
        report.append('concurrent Undo blocks stale editor saves and preserves recovery PNG')
        document = target / 'diagram.odt'
        save(doc, document)
        copy_doc.setModified(False); copy_doc.close(True)
        doc.close(True)
        # A new office process must recreate the custom object from its storage.
        installed.close(strict=True); installed.start()
        doc = installed.document(document)
        native = embedded(doc.EmbeddedObjects.getByIndex(0))
        assert native.getClassName() == 'Inlay Diagram'
        assert native.getComponent().getPropertyValue('Source') == SOURCE
        assert png(native.getComponent()) == edited
        export_pdf(doc, target / 'with-extension.pdf')
        report.append('ODT persistence and reconstruction after office restart')
        installed.close(strict=True)
        fallback.start()
        doc = fallback.document(document)
        obj = doc.EmbeddedObjects.getByIndex(0)
        assert obj.ReplacementGraphic is not None
        export_pdf(doc, target / 'without-extension.pdf')
        recipient_copy = target / 'recipient-copy.odt'
        save(doc, recipient_copy)
        with zipfile.ZipFile(recipient_copy) as archive:
            sources = [n for n in archive.namelist() if n.endswith('/source.txt')]
            assert len(sources) == 1 and archive.read(sources[0]).decode() == SOURCE
        report.append('view, PDF export and lossless ODT resave without extension')
        fallback.close(strict=True)
        installed.start()
        doc = installed.document(recipient_copy)
        assert embedded(doc.EmbeddedObjects.getByIndex(0)).getComponent().getPropertyValue('Source') == SOURCE
        report.append('editing capability restored after recipient resave')
        installed.close(strict=True)
        report.append('clean office exits at every restart and final shutdown')
        (target / 'report.json').write_text(json.dumps(report, indent=2))
        print('PASS:\n- ' + '\n- '.join(report))
        print('Artifacts:', target)
    finally:
        installed.close(); fallback.close()


if __name__ == '__main__': main()
