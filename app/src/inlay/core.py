"""Document persistence and cancellable rendering, independent of the UI."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from PIL import Image
from .png import SIGNATURE, KEYS, chunks, itxt, recover
from .source_type import detect


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_document(path):
    items = chunks(path)
    with Image.open(path) as im:
        im.verify()
    try:
        return recover(items).decode('utf8')
    except KeyError as e:
        if e.args == (b'Source',):
            raise ValueError('This PNG has no embedded Source. Use Import source to attach a script.') from e
        raise


def save_document(image, source, target, expected=None, source_type=None):
    """Write verified image+source atomically, refusing concurrent changes."""
    target = Path(target)
    items = chunks(image)
    with Image.open(image) as im:
        im.verify()
    source_type = source_type or detect(source)
    manifest = dict(version=1, sha256=hashlib.sha256(source.encode('utf8')).hexdigest(),
                    source_type=source_type,
                    contract='mermaid-v1' if source_type == 'mermaid' else 'shebang-output-argument-v1')
    parts = [SIGNATURE]
    for kind, data, raw in items:
        if kind == b'dSIG':
            raise ValueError('Cannot modify a signed PNG')
        if kind in (b'iTXt', b'tEXt', b'zTXt') and data.split(b'\0', 1)[0] in KEYS | {b'SourceType', b'SourceLanguage'}:
            continue
        if kind == b'IEND':
            parts += [itxt(b'Source', source), itxt(b'SourceType', source_type), itxt(b'SourceManifest', json.dumps(manifest))]
        parts.append(raw)
    fd, name = tempfile.mkstemp(prefix='.' + target.name + '.', suffix='.png', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(b''.join(parts)); f.flush(); os.fsync(f.fileno())
        if read_document(name) != source:
            raise ValueError('Embedded source verification failed')
        if expected is not None and (not target.exists() or fingerprint(target) != expected):
            raise ValueError('The file changed outside Inlay. Use Save As to preserve both versions.')
        if target.exists():
            os.chmod(name, target.stat().st_mode & 0o777)
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class RenderJob:
    """Run an executable source by shebang; output stays temporary until accepted."""
    def __init__(self, source, cwd, timeout=120, source_type=None):
        source_type = source_type or detect(source)
        if not source.startswith('#!') and source_type != 'python':
            raise ValueError('Add a shebang on the first line, for example #!/usr/bin/env python3')
        self.source = source
        self.timeout = timeout
        self.temp = tempfile.TemporaryDirectory(prefix='inlay-render-')
        self.directory = Path(self.temp.name)
        self.output = self.directory / 'result.png'
        script = self.directory / 'source'
        script.write_text(source, encoding='utf8'); script.chmod(0o700)
        self.log = open(self.directory / 'render.log', 'wb')
        env = os.environ.copy()
        env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env.get('PATH', '')
        try:
            command = [str(script), str(self.output)] if source.startswith('#!') else [sys.executable, str(script), str(self.output)]
            self.process = subprocess.Popen(command, cwd=cwd, env=env,
                                            stdout=self.log, stderr=subprocess.STDOUT,
                                            start_new_session=True)
        except Exception:
            self.log.close(); self.temp.cleanup(); raise
        self.started = time.monotonic()

    def poll(self):
        code = self.process.poll()
        if code is None and time.monotonic() - self.started > self.timeout:
            self.stop()
            raise TimeoutError(f'Render exceeded {self.timeout} seconds')
        if code is None:
            return False
        if code != 0:
            raise RuntimeError(f'Render exited with code {code}\n{self.diagnostics()}')
        if not self.output.is_file():
            raise ValueError('Script did not write the PNG to its first argument')
        chunks(self.output)
        with Image.open(self.output) as im:
            im.verify()
        return True

    def diagnostics(self):
        with open(self.directory / 'render.log', 'rb') as f:
            f.seek(0, 2); f.seek(max(0, f.tell() - 32000))
            return f.read().decode('utf8', errors='replace')

    def stop(self):
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait()

    def close(self):
        self.stop(); self.log.close(); self.temp.cleanup()
