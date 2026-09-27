"""External editor sessions for native Inlay objects; UNO work stays on the UI queue."""
import hashlib
import traceback
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import uno
import unohelper
from com.sun.star.awt import XCallback
from com.sun.star.document import XUndoAction
from inlay_object import parse_png


def service(ctx,name):return ctx.ServiceManager.createInstanceWithContext(name,ctx)
def checksum(data):return hashlib.sha256(data).digest()


def message(obj,text):
    try:parent=obj.parent.CurrentController.Frame.ContainerWindow if obj.parent is not None else None
    except Exception:parent=None
    box=service(obj.ctx,'com.sun.star.awt.Toolkit').createMessageBox(
        parent,uno.Enum('com.sun.star.awt.MessageBoxType','INFOBOX'),1,'Inlay',text)
    box.execute()


def find_editor():
    configured = Path.home() / '.config/inlay/libreoffice-editor'
    if configured.is_file():
        candidate = Path(configured.read_text().strip()).expanduser()
        if candidate.is_absolute() and candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        raise ValueError('The editor path in ~/.config/inlay/libreoffice-editor is not executable.')
    for candidate in (Path.home()/'.local/bin/inlay', Path.home()/'bin/inlay'):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    candidate = shutil.which('inlay')
    if candidate:
        return candidate
    raise ValueError('Install Inlay with install.sh, or put its executable path in ~/.config/inlay/libreoffice-editor.')


def editor_env():
    # LibreOffice's loader variables must not leak into the separate Qt application.
    env = os.environ.copy()
    for key in ('PYTHONHOME', 'PYTHONPATH', 'URE_BOOTSTRAP', 'UNO_PATH', 'LD_LIBRARY_PATH'):
        env.pop(key, None)
    return env



class EditUndo(unohelper.Base,XUndoAction):
    def __init__(self,obj,before,after):self.obj,self.before,self.after=obj,before,after
    @property
    def Title(self):return 'Edit Inlay diagram'
    def getTitle(self):return self.Title
    def undo(self):self.obj.setPropertyValue('PNG',uno.ByteSequence(self.before))
    def redo(self):self.obj.setPropertyValue('PNG',uno.ByteSequence(self.after))


def attached(obj):
    if obj.closed or obj.parent is None:return False
    try:
        entries=obj.parent.EmbeddedObjects
        for i in range(entries.Count):
            embedded=entries.getByIndex(i).getExtendedControlOverEmbeddedObject()
            component=embedded.getComponent()
            if component is not None and hasattr(component,'getPropertyValue'):
                try:
                    if component.getPropertyValue('ObjectIdentity')==obj.identity:return True
                except Exception:pass
    except Exception:return False
    return False


class Session(unohelper.Base,XCallback):
    def __init__(self,obj):
        self.obj=obj;self.directory=Path(tempfile.mkdtemp(prefix='inlay-object-'))
        self.path=self.directory/'diagram.png';self.path.write_bytes(obj.png)
        self.expected=checksum(obj.png);self.stop=threading.Event();self.pending=False
        self.callback=service(obj.ctx,'com.sun.star.awt.AsyncCallback');self.failure=None
        self.log=open(self.directory/'editor.log','wb')
        try:
            self.process=subprocess.Popen([find_editor(),str(self.path)],env=editor_env(),
                                          stdout=self.log,stderr=subprocess.STDOUT)
        except Exception:
            self.log.close();shutil.rmtree(self.directory);raise
        threading.Thread(target=self.watch,daemon=True).start()

    def watch(self):
        while not self.stop.wait(.35):
            try:
                ended=self.process.poll() is not None
                changed=checksum(self.path.read_bytes())!=self.expected
                if (changed or ended) and not self.pending:
                    self.pending=True;self.callback.addCallback(self,None)
                if ended:return
            except Exception as error:
                self.failure=str(error);self.callback.addCallback(self,None);return

    def notify(self,unused):
        try:
            if self.stop.is_set():return
            if self.failure:raise ValueError(self.failure)
            data=self.path.read_bytes();current=checksum(data)
            if current!=self.expected:
                if not attached(self.obj):raise ValueError('The diagram was removed or its document was closed.')
                if self.obj.isReadonly():raise ValueError('The document is read-only.')
                if checksum(self.obj.png)!=self.expected:
                    raise ValueError('The diagram changed in Writer, possibly through Undo. Automatic updates stopped.')
                parse_png(data)
                manager=self.obj.parent.getUndoManager()
                if manager.isLocked():raise ValueError('Writer Undo is locked.')
                action=EditUndo(self.obj,self.obj.png,data)
                manager.enterUndoContext(action.getTitle())
                try:
                    try:
                        action.redo();manager.addUndoAction(action)
                    except Exception:
                        action.undo()
                        raise
                finally:manager.leaveUndoContext()
                self.expected=current
            if self.process.poll() is not None:
                if self.process.returncode:raise ValueError('Inlay exited unsuccessfully; see editor.log.')
                self.finish(False)
        except Exception as error:
            (self.directory/'error.log').write_text(traceback.format_exc())
            self.finish(True)
            message(self.obj,str(error)+'\n\nYour editable PNG is kept at:\n'+str(self.path))
        finally:self.pending=False

    def finish(self,retain):
        self.stop.set();self.log.close();self.obj.session=None
        if not retain:shutil.rmtree(self.directory,ignore_errors=True)


def edit_object(obj):
    if obj.session is not None:return
    try:
        if obj.isReadonly():raise ValueError('The document is read-only.')
        if not attached(obj):raise ValueError('The diagram is no longer in its document.')
        obj.session=Session(obj)
    except Exception as error:message(obj,str(error))
