#!/usr/bin/env python3
"""Embed/recover UTF-8 diagram source without re-encoding PNG pixels."""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

SIGNATURE = b'\x89PNG\r\n\x1a\n'
KEYS = {b'Source', b'SourceManifest'}


def chunks(path):
    data = Path(path).read_bytes()
    if not data.startswith(SIGNATURE):
        raise ValueError('Not a PNG')
    pos = 8
    result = []
    while pos < len(data):
        n = struct.unpack('>I', data[pos:pos+4])[0]
        end = pos + n + 12
        raw = data[pos:end]
        if len(raw) != n + 12:
            raise ValueError('Truncated PNG')
        kind, payload = raw[4:8], raw[8:-4]
        if zlib.crc32(kind + payload) != struct.unpack('>I', raw[-4:])[0]:
            raise ValueError('PNG CRC mismatch')
        result.append((kind, payload, raw))
        pos = end
        if kind == b'IEND':
            if pos != len(data):
                raise ValueError('Unexpected trailing PNG data')
            return result
    raise ValueError('Missing IEND')


def text_field(kind, data):
    key, rest = data.split(b'\0', 1)
    if kind == b'tEXt':
        return key, rest.decode('latin1')
    if kind == b'zTXt':
        if rest[0] != 0:
            raise ValueError('Unknown compression')
        return key, zlib.decompress(rest[1:]).decode('latin1')
    flag, method = rest[:2]
    _, _, value = rest[2:].split(b'\0', 2)
    if flag not in (0, 1) or method != 0:
        raise ValueError('Unknown iTXt encoding')
    return key, (zlib.decompress(value) if flag else value).decode('utf8')


def recover(items):
    fields = {}
    for kind, data, _ in items:
        if kind in (b'iTXt', b'tEXt', b'zTXt') and data.split(b'\0', 1)[0] in KEYS:
            key, value = text_field(kind, data)
            if key in fields:
                raise ValueError('Duplicate source metadata')
            fields[key] = value
    source = fields[b'Source'].encode('utf8')
    if b'SourceManifest' in fields:
        manifest = json.loads(fields[b'SourceManifest'])
        if manifest['sha256'] != hashlib.sha256(source).hexdigest():
            raise ValueError('Source checksum mismatch')
    return source


def itxt(key, value):
    payload = key + b'\0\0\0\0\0' + value.encode('utf8')
    body = b'iTXt' + payload
    return struct.pack('>I', len(payload)) + body + struct.pack('>I', zlib.crc32(body))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    e = sub.add_parser('embed')
    e.add_argument('image'); e.add_argument('source')
    e.add_argument('--output', required=True)
    e.add_argument('--source-type', required=True, choices=['python','mermaid','shell','executable','unknown'])
    e.add_argument('--render-command', default='')
    e.add_argument('--requirements', default='')
    v = sub.add_parser('verify')
    v.add_argument('image'); v.add_argument('source')
    x = sub.add_parser('extract')
    x.add_argument('image'); x.add_argument('--output', required=True)
    a = p.parse_args()
    items = chunks(a.image)
    if a.action == 'embed':
        source = Path(a.source).read_bytes()
        value = source.decode('utf8')
        manifest = dict(version=1, filename=Path(a.source).name,
                        sha256=hashlib.sha256(source).hexdigest(), source_type=a.source_type,
                        render_command=a.render_command, requirements=a.requirements)
        parts = [SIGNATURE]
        for kind, data, raw in items:
            if kind == b'dSIG':
                raise ValueError('Refusing to invalidate a signed PNG')
            if kind in (b'iTXt', b'tEXt', b'zTXt') and data.split(b'\0', 1)[0] in KEYS | {b'SourceType', b'SourceLanguage'}:
                continue
            if kind == b'IEND':
                parts += [itxt(b'Source', value), itxt(b'SourceType', a.source_type), itxt(b'SourceManifest', json.dumps(manifest, ensure_ascii=False))]
            parts.append(raw)
        with open(a.output, 'xb') as f:
            f.write(b''.join(parts))
        if recover(chunks(a.output)) != source:
            raise ValueError('Round-trip verification failed')
    else:
        source = recover(items)
        if a.action == 'verify':
            if source != Path(a.source).read_bytes():
                raise ValueError('Embedded source differs from sidecar')
        else:
            with open(a.output, 'xb') as f:
                f.write(source)
    print('OK:', a.action)


if __name__ == '__main__':
    main()
