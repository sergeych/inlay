"""One persistent local Mermaid renderer, lazily created for Mermaid documents."""
import json
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot, QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PySide6.QtWebEngineWidgets import QWebEngineView


class LocalOnly(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, request):
        if request.requestUrl().scheme() not in ('file', 'qrc', 'data', 'blob', 'about'):
            request.block(True)


class Bridge(QObject):
    ready = Signal()
    result = Signal(int, str, str)

    @Slot()
    def loaded(self): self.ready.emit()

    @Slot(int, str, str)
    def finished(self, revision, png, error): self.result.emit(revision, png, error)


class MermaidView(QWebEngineView):
    result = Signal(int, str, str)

    def __init__(self):
        super().__init__()
        self.is_ready = False
        self.waiting = None
        self.channel = QWebChannel(self.page())
        self.bridge = Bridge(self.channel)
        self.channel.registerObject('bridge', self.bridge)
        self.page().setWebChannel(self.channel)
        self.interceptor = LocalOnly(self)
        self.page().profile().setUrlRequestInterceptor(self.interceptor)
        self.bridge.ready.connect(self.loaded)
        self.bridge.result.connect(self.result)
        self.setUrl(QUrl.fromLocalFile(str(Path(__file__).parent / 'web' / 'index.html')))

    def loaded(self):
        self.is_ready = True
        if self.waiting:
            self.submit(*self.waiting); self.waiting = None

    def submit(self, revision, source):
        if not self.is_ready:
            self.waiting = (revision, source); return
        self.page().runJavaScript(f'window.requestRender({revision}, {json.dumps(source)})')

    def invalidate(self, revision):
        self.waiting = None
        if self.is_ready:
            self.page().runJavaScript(f'window.invalidate({revision})')

    def restart(self):
        self.is_ready = False; self.waiting = None
        self.reload()

    def fit(self): self.page().runJavaScript('window.fitDiagram()')
    def zoom(self, factor): self.page().runJavaScript(f'window.zoomDiagram({factor})')
