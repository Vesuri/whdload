"""Unpack the game executable for static analysis.

    python3 tools/exe.py [FILE]      (default tmp/game/AlienBreed3DAGA/data/ABD.PK)

Decrunches the RNC (ProPack method 1) file, checking both CRC16s in its header, and writes
tmp/exe/abd (the hunk executable) and tmp/exe/abd.flat: the hunks laid end to end and
relocated to 0, so an address in it is the offset resload_PatchSeg patch lists use (the
offsets in docs/internals.md). Prints each hunk's offset, size and memory type, and the
CRC16 the slave's version check sees. Disassemble with
    m68k-amiga-elf-objdump -D -b binary -m m68k:68020 --start-address=A tmp/exe/abd.flat
"""
import os
import struct
import sys

GAME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def crc16(data):
    """CRC-16/ARC, as RNC headers and resload_CRC16 compute it."""
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ 0xa001 if c & 1 else c >> 1
        table.append(c)
    c = 0
    for b in data:
        c = table[(c ^ b) & 0xff] ^ (c >> 8)
    return c


class _Bits:
    """RNC1's bit reader: little-endian words, bits taken from the bottom, one word ahead."""

    def __init__(self, data, pos):
        self.d, self.p = data, pos
        self.buf, self.n = self._word(pos), 16

    def _word(self, p):
        return int.from_bytes(self.d[p:p + 2].ljust(2, b'\0'), 'little')

    def peek(self, mask):
        return self.buf & mask

    def skip(self, n):
        self.buf >>= n
        self.n -= n
        if self.n < 16:
            self.p += 2
            self.buf |= self._word(self.p) << self.n
            self.n += 16

    def read(self, n):
        v = self.buf & ((1 << n) - 1)
        self.skip(n)
        return v

    def resync(self):
        """After literal bytes: drop the look-ahead word, which was literal data."""
        self.n -= 16
        self.buf &= (1 << self.n) - 1
        self.buf |= self._word(self.p) << self.n
        self.n += 16


def _table(bits):
    count = bits.read(5)
    if not count:
        return []
    lengths = [bits.read(4) for _ in range(count)]
    table, code = [], 0
    for length in range(1, max(lengths) + 1):
        for value, l in enumerate(lengths):
            if l == length:
                table.append((int(format(code, '0%db' % length)[::-1], 2), length, value))
                code += 1
        code <<= 1
    return table


def _symbol(table, bits):
    for code, length, value in table:
        if bits.peek((1 << length) - 1) == code:
            bits.skip(length)
            if value >= 2:
                value = (1 << (value - 1)) | bits.read(value - 1)
            return value
    raise ValueError('no Huffman code matches at input offset %#x' % bits.p)


def unrnc(data):
    if data[:4] != b'RNC\x01':
        raise ValueError('not an RNC method 1 file')
    size, packed, crc, packed_crc = struct.unpack('>IIHH', data[4:16])
    if crc16(data[18:18 + packed]) != packed_crc:
        raise ValueError('packed data CRC differs')
    bits = _Bits(data, 18)
    bits.skip(2)
    out = bytearray()
    while len(out) < size:
        raw, dist, length = _table(bits), _table(bits), _table(bits)
        count = bits.read(16)
        while True:
            n = _symbol(raw, bits)
            if n:
                out += data[bits.p:bits.p + n]
                bits.p += n
                bits.resync()
            count -= 1
            if count <= 0:
                break
            back = _symbol(dist, bits) + 1
            for _ in range(_symbol(length, bits) + 2):
                out.append(out[-back])
    if len(out) != size or crc16(out) != crc:
        raise ValueError('unpacked data CRC differs')
    return bytes(out)


def flatten(exe):
    """Hunks end to end, relocated to 0: [(offset, size, memory)], image."""
    words = lambda p: struct.unpack('>I', exe[p:p + 4])[0]
    if words(0) != 0x3f3:
        raise ValueError('not a hunk executable')
    p = 4
    while words(p):
        p += 4 + 4 * words(p)
    p += 4
    first, last = words(p + 4), words(p + 8)
    p += 12
    sizes = [words(p + 4 * i) for i in range(last - first + 1)]
    p += 4 * len(sizes)
    hunks, offset = [], 0
    for s in sizes:
        hunks.append((offset, (s & 0x3fffffff) * 4, ('any', 'chip', 'fast', '?')[s >> 30]))
        offset += (s & 0x3fffffff) * 4
    image = bytearray(offset)
    relocs, h = [], -1
    while p < len(exe):
        kind = words(p) & 0x3fffffff
        p += 4
        if kind in (0x3e9, 0x3ea):
            h += 1
            n = words(p) * 4
            image[hunks[h][0]:hunks[h][0] + n] = exe[p + 4:p + 4 + n]
            p += 4 + n
        elif kind == 0x3eb:
            h += 1
            p += 4
        elif kind == 0x3ec:
            while words(p):
                n, target = words(p), words(p + 4)
                relocs += [(h, words(p + 8 + 4 * i), target) for i in range(n)]
                p += 8 + 4 * n
            p += 4
        elif kind == 0x3f2:
            pass
        else:
            raise ValueError('hunk type %#x at %#x' % (kind, p - 4))
    for h, at, target in relocs:
        a = hunks[h][0] + at
        v = struct.unpack('>I', image[a:a + 4])[0] + hunks[target][0]
        image[a:a + 4] = struct.pack('>I', v & 0xffffffff)
    return hunks, bytes(image), len(relocs)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(GAME, 'tmp/game/AlienBreed3DAGA/data/ABD.PK')
    data = open(src, 'rb').read()
    exe = unrnc(data) if data[:3] == b'RNC' else data
    out = os.path.join(GAME, 'tmp/exe')
    os.makedirs(out, exist_ok=True)
    hunks, image, nrelocs = flatten(exe)
    open(os.path.join(out, 'abd'), 'wb').write(exe)
    open(os.path.join(out, 'abd.flat'), 'wb').write(image)
    print('%s: %d bytes, CRC16 $%04x' % (os.path.basename(src), len(exe), crc16(exe)))
    for i, (offset, size, memory) in enumerate(hunks):
        print('hunk %d  $%06x-$%06x  %-4s %d bytes' % (i, offset, offset + size, memory, size))
    print('%d relocations; wrote tmp/exe/abd and tmp/exe/abd.flat' % nrelocs)


if __name__ == '__main__':
    main()
