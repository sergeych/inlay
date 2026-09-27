import time
from pathlib import Path
import pytest
from PIL import Image
from inlay.core import RenderJob, fingerprint, read_document, save_document
from inlay.png import chunks

SOURCE = '''#!/usr/bin/env python3
import sys
from PIL import Image
Image.new('RGB', (40, 30), 'red').save(sys.argv[1])
# Unicode: исходник
'''


def finish(job):
    until = time.monotonic() + 10
    while not job.poll():
        assert time.monotonic() < until
        time.sleep(.02)


def test_render_save_reopen_preserves_pixels_and_unicode(tmp_path):
    job = RenderJob(SOURCE, tmp_path)
    try:
        finish(job)
        out = tmp_path / 'diagram.png'
        save_document(job.output, SOURCE, out)
        assert read_document(out) == SOURCE
        assert Image.open(out).getpixel((0, 0)) == (255, 0, 0)
        assert [r for k,d,r in chunks(out) if k == b'IDAT'] == [r for k,d,r in chunks(job.output) if k == b'IDAT']
    finally: job.close()


def test_save_refuses_external_changes(tmp_path):
    raw = tmp_path / 'raw.png'; Image.new('RGB', (3, 3)).save(raw)
    out = tmp_path / 'out.png'; save_document(raw, SOURCE, out)
    expected = fingerprint(out)
    out.write_bytes(b'someone changed this')
    with pytest.raises(ValueError, match='outside'):
        save_document(raw, SOURCE, out, expected)
    assert out.read_bytes() == b'someone changed this'


@pytest.mark.parametrize('body, message', [
    ('raise RuntimeError("broken")', 'broken'),
    ('pass', 'did not write'),
    ('import sys; open(sys.argv[1], "w").write("not png")', 'Not a PNG'),
])
def test_failed_renders(tmp_path, body, message):
    job = RenderJob('#!/usr/bin/env python3\n' + body, tmp_path)
    try:
        with pytest.raises((ValueError, RuntimeError), match=message): finish(job)
    finally: job.close()


def test_stop_and_timeout(tmp_path):
    job = RenderJob('#!/usr/bin/env python3\nimport time; time.sleep(20)', tmp_path, timeout=.05)
    try:
        time.sleep(.08)
        with pytest.raises(TimeoutError): job.poll()
        assert job.process.poll() is not None
    finally: job.close()


def test_requires_shebang(tmp_path):
    with pytest.raises(ValueError, match='shebang'): RenderJob('print(1)', tmp_path)


def test_python_without_shebang(tmp_path):
    job = RenderJob(SOURCE.split('\n', 1)[1], tmp_path)
    try: finish(job)
    finally: job.close()


def test_shebang_supports_other_languages(tmp_path):
    raw = tmp_path / 'input.png'; Image.new('RGB', (5, 5)).save(raw)
    job = RenderJob('#!/bin/sh\ncp input.png "$1"\n', tmp_path)
    try:
        finish(job)
        assert job.output.read_bytes() == raw.read_bytes()
    finally: job.close()
