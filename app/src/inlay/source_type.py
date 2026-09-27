"""Conservative source recognition; explicit metadata always wins."""
import ast
import json
import re
from .png import chunks, text_field

TYPES = ('python', 'mermaid', 'shell', 'executable', 'unknown')
ALIASES = {'py': 'python', 'python3': 'python', 'mmd': 'mermaid',
           'text/x-python': 'python', 'text/vnd.mermaid': 'mermaid', 'sh': 'shell', 'bash': 'shell'}


def normalize(value):
    value = value.strip().lower()
    return ALIASES.get(value, value if value in TYPES else 'unknown')


def detect(source):
    text = source.lstrip('\ufeff').strip()
    first = text.split('\n', 1)[0]
    if first.startswith('#!'):
        if re.search(r'\bpython(?:\d+(?:\.\d+)*)?\b', first): return 'python'
        if re.search(r'\b(?:ba|da|z|k)?sh\b', first): return 'shell'
        return 'executable'
    if text.startswith('---\n'):
        sections = text.split('\n---', 1)
        if len(sections) == 2: text = sections[1].lstrip()
    text = '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('%%')).lstrip()
    if re.match(r'^(?:flowchart|graph|sequenceDiagram|classDiagram|stateDiagram(?:-v2)?|erDiagram|gantt|pie|journey|gitGraph|mindmap|timeline|quadrantChart|requirementDiagram|sankey(?:-beta)?|xychart(?:-beta)?|block(?:-beta)?|packet(?:-beta)?|architecture(?:-beta)?|radar(?:-beta)?|treemap(?:-beta)?|kanban|zenuml|C4\w+)\b', text):
        return 'mermaid'
    try:
        tree = ast.parse(source)
        if any(isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for n in ast.walk(tree)):
            return 'python'
    except SyntaxError:
        # While editing, a broken Python expression should not lose its language.
        if re.search(r'(?m)^(?:from\s+[\w.]+\s+import\b|import\s+[\w.]+|(?:async\s+)?def\s+\w+\s*\()', source):
            return 'python'
    return 'unknown'


def document_type(path, source):
    fields = {}
    for kind, data, _ in chunks(path):
        if kind in (b'iTXt', b'tEXt', b'zTXt') and data.split(b'\0', 1)[0] in (b'SourceType', b'SourceManifest', b'SourceLanguage'):
            key, value = text_field(kind, data); fields[key] = value
    if b'SourceType' in fields: return normalize(fields[b'SourceType'])
    if b'SourceManifest' in fields:
        manifest = json.loads(fields[b'SourceManifest'])
        if 'source_type' in manifest: return normalize(manifest['source_type'])
    language = fields.get(b'SourceLanguage', '').lower()
    if language.startswith('python'): return 'python'
    if language.startswith('mermaid'): return 'mermaid'
    return detect(source)
