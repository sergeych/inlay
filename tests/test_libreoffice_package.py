"""The OXT must carry its complete standalone implementation and starter source."""
from pathlib import Path
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from inlay.png import chunks, recover

ROOT = Path(__file__).resolve().parents[1]


def test_oxt_is_self_contained_and_default_diagram_is_editable(tmp_path):
    subprocess.run([sys.executable, str(ROOT / 'tools/build_libreoffice.py')], check=True)
    with zipfile.ZipFile(ROOT / 'dist/inlay-writer-0.1.0.oxt') as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        manifest = ET.fromstring(archive.read('META-INF/manifest.xml'))
        ns = '{http://openoffice.org/2001/manifest}'
        for item in manifest:
            assert item.attrib[ns + 'full-path'] in names
        for name in names:
            if name.endswith(('.xml', '.xcu')): ET.fromstring(archive.read(name))
            if name.endswith('.py'): compile(archive.read(name), name, 'exec')
        assert archive.read('pythonpath/inlay_png.py') == (ROOT / 'app/src/inlay/png.py').read_bytes()
        assert 'pythonpath/inlay_session.py' in names
        assert 'pythonpath/inlay_object.py' in names
        image = tmp_path / 'default.png'
        image.write_bytes(archive.read('pythonpath/default.png'))
        assert recover(chunks(image)) == archive.read('pythonpath/default.mmd')
