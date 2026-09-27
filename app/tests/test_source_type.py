import pytest
from PIL import Image, PngImagePlugin
from inlay.source_type import detect, document_type
from inlay.core import save_document, read_document


@pytest.mark.parametrize('source,kind', [
    ('flowchart LR\n A-->B', 'mermaid'),
    ('%% comment\nsequenceDiagram\n Alice->>Bob: Hello', 'mermaid'),
    ('---\ntitle: Example\n---\nclassDiagram\nclass A', 'mermaid'),
    ('stateDiagram-v2\n[*]-->A', 'mermaid'),
    ('import os\nprint(', 'python'),
    ('from PIL import Image\nImage.new("RGB",(10,10))', 'python'),
    ('def draw():\n    pass', 'python'),
    ('#!/usr/bin/env python3\nprint(1)', 'python'),
    ('#!/bin/sh\necho hello', 'shell'),
    ('#!/usr/bin/ruby\nputs 1', 'executable'),
    ('some random words', 'unknown'),
    ('A --> B', 'unknown'),
])
def test_detection(source, kind): assert detect(source) == kind


def test_metadata_priority_and_roundtrip(tmp_path):
    raw=tmp_path/'raw.png'; out=tmp_path/'out.png'
    meta=PngImagePlugin.PngInfo()
    meta.add_itxt('SourceType','something-unsupported')
    meta.add_itxt('SourceLanguage','Python 3 / Pillow')
    Image.new('RGB',(20,20)).save(raw,pnginfo=meta)
    assert document_type(raw,'flowchart LR\n A-->B')=='unknown'
    source='flowchart LR\n A-->B'
    save_document(raw,source,out,source_type='mermaid')
    assert document_type(out,source)=='mermaid'
    assert read_document(out)==source
    image=Image.open(out);image.load()
    assert image.info['SourceType']=='mermaid'
    assert 'SourceLanguage' not in image.info


def test_legacy_language_metadata(tmp_path):
    meta=PngImagePlugin.PngInfo();meta.add_itxt('SourceLanguage','Python 3 / Pillow')
    p=tmp_path/'old.png';Image.new('RGB',(5,5)).save(p,pnginfo=meta)
    assert document_type(p,'broken source')=='python'
