"""Add the public OCS toggle to the pinned launch icon, preserving its artwork.

Length-prefixed tooltype approach shared with Their Finest Hour packaging.
Only newly generated icons are modified; reference/user icons stay untouched.
"""
import struct


def tooltypes(data):
    marker = b'\x00\x00\x00\x08WHDLoad\x00'
    if data[:2] != b'\xe3\x10' or data.count(marker) != 1:
        raise ValueError('unsupported OCS icon/default tool')
    start = data.index(marker) + len(marker)
    size = struct.unpack_from('>I', data, start)[0]
    if size < 4 or size % 4 or size > len(data):
        raise ValueError('invalid tooltype array size')
    cursor, entries = start + 4, []
    for _ in range(size // 4 - 1):
        length = struct.unpack_from('>I', data, cursor)[0]
        cursor += 4
        value = data[cursor:cursor + length]
        if not length or len(value) != length or not value.endswith(b'\0'):
            raise ValueError('invalid tooltype string')
        entries.append(value)
        cursor += length
    return start, cursor, entries


def enhanced_icon(original):
    start, end, entries = tooltypes(original)
    if b'SLAVE=WINGCOMMANDER.SLAVE\0' not in [x.upper() for x in entries]:
        raise ValueError('icon does not select OCS slave')
    if any(x.upper().lstrip(b'(').startswith(b'CUSTOM5=') for x in entries):
        raise ValueError('refusing to replace existing CUSTOM5 choice')
    added = [b'CUSTOM5=1\0']
    if not any(x.rstrip(b'\0').upper() in (b'CACHE', b'DCACHE', b'NOCACHE') for x in entries):
        added.append(b'DCACHE\0')
    addition = b''.join(struct.pack('>I', len(entry)) + entry for entry in added)
    size = struct.unpack_from('>I', original, start)[0]
    updated = original[:start] + struct.pack('>I', size+4*len(added)) + addition + original[start+4:]
    if tooltypes(updated)[2] != added + entries:
        raise ValueError('tooltype insertion failed')
    if updated[:start]+struct.pack('>I',size)+updated[start+4+len(addition):] != original:
        raise ValueError('icon artwork changed')
    return updated
