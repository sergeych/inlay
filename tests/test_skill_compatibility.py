from pathlib import Path
import subprocess
import sys
import zipfile
from PIL import Image
from inlay.core import read_document, save_document

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'skills/inlay/scripts/png_source.py'


def test_portable_helper_and_editor_interoperate(tmp_path):
    raw = tmp_path / 'raw.png'
    Image.new('RGB', (12, 12), 'blue').save(raw)
    source = tmp_path / 'diagram.mmd'
    source.write_bytes('flowchart LR\n A[Привет] --> B\n'.encode())
    embedded = tmp_path / 'embedded.png'
    subprocess.run([sys.executable, str(HELPER), 'embed', str(raw), str(source),
                    '--output', str(embedded), '--source-type', 'mermaid'], check=True, cwd=tmp_path)
    assert read_document(embedded).encode() == source.read_bytes()
    saved = tmp_path / 'saved.png'
    save_document(raw, source.read_text(), saved, source_type='mermaid')
    recovered = tmp_path / 'recovered.mmd'
    subprocess.run([sys.executable, str(HELPER), 'extract', str(saved),
                    '--output', str(recovered)], check=True, cwd=tmp_path)
    assert recovered.read_bytes() == source.read_bytes()


def test_skill_archive_works_outside_checkout(tmp_path):
    subprocess.run([sys.executable, str(ROOT / 'tools/build_skill.py')], check=True, cwd=tmp_path)
    with zipfile.ZipFile(ROOT / 'dist/inlay-skill.zip') as archive:
        archive.extractall(tmp_path)
    helper = tmp_path / 'inlay/scripts/png_source.py'
    subprocess.run([sys.executable, str(helper), 'verify', str(ROOT / 'examples/trust.png'),
                    str(ROOT / 'examples/trust.mmd')], check=True, cwd=tmp_path)
