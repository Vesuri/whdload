"""Shared WCFS/WCDS wire format. Timing and ownership policy belong to adapters."""
import struct

NAMES = {1: 'loop', 2: 'world_begin', 3: 'world_end', 4: 'draw', 5: 'predicted',
         6: 'scene_drawn', 7: 'hud_done', 8: 'restored', 9: 'convert_entry',
         10: 'limit_begin', 11: 'limit_end', 12: 'convert_begin', 13: 'convert_end',
         14: 'wait_begin', 15: 'wait_end', 16: 'queued',
         17: 'render_complete', 18: 'native_publication'}


def encode_frames(hz, rows, skip=0):
    if hz not in (50, 60) or not 0 <= skip <= 0xffffffff:
        raise ValueError('invalid frame header')
    words = []
    for event, field, line in rows:
        if event not in NAMES or not 0 <= field < 0x40000 or not 0 <= line < (313 if hz == 50 else 263):
            raise ValueError('invalid frame record')
        words.append((event << 27) | (field << 9) | line)
    return struct.pack('>4sIII', b'WCFS', hz, len(words), skip) + b''.join(struct.pack('>I', w) for w in words)


def decode_frames(raw):
    if len(raw) < 16:
        raise ValueError('truncated frame header')
    magic, hz, count, skip = struct.unpack_from('>4sIII', raw)
    if magic != b'WCFS' or hz not in (50, 60) or len(raw) != 16+4*count:
        raise ValueError('invalid frame statistics file')
    rows = [(w >> 27, (w >> 9) & 0x3ffff, w & 0x1ff)
            for (w,) in struct.iter_unpack('>I', raw[16:])]
    # One implementation of the range contract in both directions.
    if encode_frames(hz, rows, skip) != raw:
        raise ValueError('noncanonical frame record')
    return hz, skip, rows


def encode_display(hz, rows):
    """16-byte base ledger; the existing CD32 32-byte extension is also readable."""
    raw = struct.pack('>4sIII', b'WCDS', hz, len(rows), 16)
    raw += b''.join(struct.pack('>IHHII', *row) for row in rows)
    decode_display(raw)
    return raw


def decode_display(raw):
    if len(raw) < 16:
        raise ValueError('truncated display header')
    magic, hz, count, size = struct.unpack_from('>4sIII', raw)
    if magic != b'WCDS' or hz not in (50, 60) or size not in (16, 32) or len(raw) != 16+size*count:
        raise ValueError('invalid display ledger')
    rows = [struct.unpack_from('>IHHII', raw, 16+i*size) for i in range(count)]
    if any(v >= (313 if hz == 50 else 263) or index > 1 or not plane or not copper
           for f, v, index, plane, copper in rows):
        raise ValueError('invalid display record')
    return hz, size, rows


def display_order(rows):
    """One newly displayed buffer per field; no chipset-specific beam deadline."""
    if any(b[0] <= a[0] or b[2] == a[2] or b[3] == a[3]
           for a, b in zip(rows, rows[1:])):
        raise ValueError('display ownership/order violated')
