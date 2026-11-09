#!/usr/bin/env python3
"""The release's game icons: Galahad's two with NOCACHE replaced by CUSTOM2=1.

    python3 tools/icons.py OUTDIR      write BattleHawks1942.newicon and .coloricon to OUTDIR
    python3 tools/icons.py --show ICON...   print each icon's default tool and tooltypes

Both icons Galahad's installer offers carry NOCACHE, which v1.0 needed (BH writes code) and
which would keep 2.0b's caches off (WHDLoad's NoCache makes resload_SetCPU do nothing).
Installer 43.3 cannot remove it: its settooltype finds no existing tooltype (setting one
appends another), and rewriting an icon through OS 3.1's icon.library drops an OS 3.5
icon's colour image. So the archive ships the icons already changed: the NOCACHE entry
becomes CUSTOM2=1 (Enhanced framerate) in place, before NewIcon's image lines, and every
other byte stays as Galahad's.  Input: tmp/game/BattleHawks1942HD (make unpack).

An icon is a DiskObject (78 bytes), the optional DrawerData, the gadget images and the
default tool, then the tooltype array: a long holding 4 * (entries + 1), then each entry
as a length-prefixed, NUL-terminated string. A trailing OS 3.5 FORM ICON stays untouched.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tmp/game/BattleHawks1942HD'
ICONS = ('BattleHawks1942.newicon', 'BattleHawks1942.coloricon')
OLD, NEW = b'NOCACHE', b'CUSTOM2=1'


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
    """(default tool, [(tooltype, its offset)], end of the tooltype array)."""
    if data[:2] != b'\xe3\x10' or len(data) < 78:
        raise ValueError('not a DiskObject')
    select = struct.unpack_from('>I', data, 26)[0]
    tool_ptr, types_ptr = struct.unpack_from('>II', data, 50)
    drawer = struct.unpack_from('>I', data, 66)[0]
    pos = _image_end(data, 78 + (56 if drawer else 0))
    if select:
        pos = _image_end(data, pos)
    tool = None
    if tool_ptr:
        tool, pos = _string(data, pos)
    if not types_ptr:
        return tool, [], pos
    size = struct.unpack_from('>I', data, pos)[0]
    if size < 4 or size % 4:
        raise ValueError('bad tooltype array size')
    pos += 4
    entries = []
    for _ in range(size // 4 - 1):
        start = pos
        value, pos = _string(data, pos)
        entries.append((value, start))
    return tool, entries, pos


def replaced(data, old, new):
    """data with the tooltype old replaced by new; nothing else changes."""
    tool, entries, end = parse(data)
    hits = [pos for value, pos in entries if value == old]
    if len(hits) != 1:
        raise ValueError(f'expected one {old!r} tooltype, found {len(hits)}')
    pos = hits[0]
    entry = struct.pack('>I', len(new) + 1) + new + b'\0'
    out = data[:pos] + entry + data[pos + 4 + len(old) + 1:]
    tool2, entries2, end2 = parse(out)
    want = [new if value == old else value for value, _ in entries]
    if tool2 != tool or [v for v, _ in entries2] != want or out[end2:] != data[end:]:
        raise ValueError('tooltype replacement did not parse back')
    return out


def main(argv):
    if argv[:1] == ['--show']:
        for path in argv[1:]:
            tool, entries, _ = parse(Path(path).read_bytes())
            shown = [v.decode('latin-1') for v, _ in entries if not v.startswith(b'IM')]
            print(f'{path}: tool {tool and tool.decode("latin-1")}; tooltypes {shown}')
        return
    if len(argv) != 1:
        sys.exit(__doc__)
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    for name in ICONS:
        (out / name).write_bytes(replaced((SOURCE / name).read_bytes(), OLD, NEW))
        print(f'{out / name}: {OLD.decode()} -> {NEW.decode()}')


if __name__ == '__main__':
    main(sys.argv[1:])
