#!/usr/bin/env python3
"""Read and extend a Workbench icon's (DiskObject's) tooltypes, keeping every other byte.

    python3 tools/icon.py ICON...      print each icon's default tool and tooltypes

The parser walks the DiskObject (78 bytes), the optional DrawerData, both gadget images
and the default tool to reach the tooltype array: a long holding 4 * (entries + 1),
then each entry as a length-prefixed, NUL-terminated string. Any NewIcon tooltypes and a
trailing ColorIcon (FORM ICON) chunk stay untouched.
"""
import struct
import sys


def _image_end(data, pos):
    width, height, depth = struct.unpack_from('>HHH', data, pos + 4)
    return pos + 20 + (width + 15) // 16 * 2 * height * depth


def _string(data, pos):
    length = struct.unpack_from('>I', data, pos)[0]
    value = data[pos + 4:pos + 4 + length]
    if not length or len(value) != length or not value.endswith(b'\0'):
        raise ValueError(f'bad icon string at {pos}')
    return value[:-1], pos + 4 + length


def parse(data):
    """(default tool, [tooltypes], tooltype array start, its end)."""
    if data[:2] != b'\xe3\x10' or len(data) < 78:
        raise ValueError('not a DiskObject')
    select = struct.unpack_from('>I', data, 26)[0]
    tool_ptr, types_ptr = struct.unpack_from('>II', data, 50)
    drawer = struct.unpack_from('>I', data, 66)[0]
    pos = 78 + (56 if drawer else 0)
    pos = _image_end(data, pos)
    if select:
        pos = _image_end(data, pos)
    tool = None
    if tool_ptr:
        tool, pos = _string(data, pos)
    if not types_ptr:
        return tool, [], pos, pos
    start = pos
    size = struct.unpack_from('>I', data, pos)[0]
    if size < 4 or size % 4:
        raise ValueError('bad tooltype array size')
    pos += 4
    entries = []
    for _ in range(size // 4 - 1):
        value, pos = _string(data, pos)
        entries.append(value)
    return tool, entries, start, pos


def with_tooltype(data, entry):
    """data with entry appended to the tooltype array; nothing else changes."""
    tool, entries, start, end = parse(data)
    if not struct.unpack_from('>I', data, 54)[0]:
        raise ValueError('icon has no tooltype array')
    size = struct.unpack_from('>I', data, start)[0]
    added = struct.pack('>I', len(entry) + 1) + entry + b'\0'
    updated = (data[:start] + struct.pack('>I', size + 4) + data[start + 4:end] + added
               + data[end:])
    _, new_entries, _, new_end = parse(updated)
    if new_entries != entries + [entry] or new_end != end + len(added):
        raise ValueError('tooltype insertion did not parse back')
    if (updated[:start] + struct.pack('>I', size) + updated[start + 4:end]
            + updated[end + len(added):]) != data:
        raise ValueError('tooltype insertion changed other bytes')
    return updated


def main():
    for path in sys.argv[1:]:
        tool, entries, _, _ = parse(open(path, 'rb').read())
        shown = tool.decode('latin-1') if tool is not None else '-'
        print(f'{path}: tool {shown}; tooltypes '
              + ', '.join(e.decode('latin-1') for e in entries))


if __name__ == '__main__':
    main()
