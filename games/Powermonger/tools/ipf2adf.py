"""Decode the AmigaDOS tracks of an IPF into a 901120-byte sector image.

python3 -I ipf2adf.py CAPSIMG.so IN.ipf OUT.adf
Sectors that are missing or fail their checksums are zero-filled and reported.
"""
import ctypes as C
import sys

import numpy as np

lib = C.CDLL(sys.argv[1])
src, out = sys.argv[2].encode(), sys.argv[3]


class TrackT1(C.Structure):
    _pack_ = 1
    _fields_ = [("type", C.c_uint32), ("cylinder", C.c_uint32), ("head", C.c_uint32),
                ("sectorcnt", C.c_uint32), ("sectorsize", C.c_uint32),
                ("trackbuf", C.POINTER(C.c_ubyte)), ("tracklen", C.c_uint32),
                ("timelen", C.c_uint32), ("timebuf", C.POINTER(C.c_uint32)),
                ("overlap", C.c_int32)]


DI_LOCK_INDEX, DI_LOCK_DENVAR, DI_LOCK_UPDATEFD, DI_LOCK_TYPE = 1, 4, 1 << 8, 1 << 9
assert lib.CAPSInit() == 0
img = lib.CAPSAddImage()
assert img >= 0
assert lib.CAPSLockImage(img, C.c_char_p(src)) == 0, "CAPSLockImage failed"
lib.CAPSLoadImage(img, DI_LOCK_DENVAR)

M = 0x55555555
SYNC = np.unpackbits(np.frombuffer(bytes.fromhex("44894489"), np.uint8))


def longs(bits, pos, n):
    """n big-endian 32-bit words from bit position pos."""
    b = np.packbits(bits[pos:pos + 32 * n])
    return np.frombuffer(b.tobytes(), ">u4").astype(np.uint64)


def dec(odd, even):
    return ((odd & M) << 1) | (even & M)


image = bytearray(901120)
bad = []
for cyl in range(80):
    for head in range(2):
        t = TrackT1(type=1)
        r = lib.CAPSLockTrack(C.byref(t), img, cyl, head,
                              DI_LOCK_INDEX | DI_LOCK_DENVAR | DI_LOCK_UPDATEFD | DI_LOCK_TYPE)
        track = cyl * 2 + head
        found = {}
        if r == 0 and t.tracklen:
            raw = np.ctypeslib.as_array(t.trackbuf, (t.tracklen,)).copy()
            bits = np.unpackbits(np.concatenate([raw, raw]))
            win = np.lib.stride_tricks.sliding_window_view(bits[:len(bits) - 32 * 300], 32)
            for p in np.nonzero((win == SYNC).all(axis=1))[0]:
                p += 32
                info = dec(*longs(bits, p, 2))
                fmt, trk, sec = int(info) >> 24, (int(info) >> 16) & 255, (int(info) >> 8) & 255
                if fmt != 0xFF or trk != track or sec > 10 or sec in found:
                    continue
                hdr = longs(bits, p, 10)
                hsum = 0
                for w in hdr:
                    hsum ^= int(w)
                if (hsum & M) != int(dec(*longs(bits, p + 320, 2))):
                    continue
                d = longs(bits, p + 448, 256)
                dsum = 0
                for w in d:
                    dsum ^= int(w)
                if (dsum & M) != int(dec(*longs(bits, p + 384, 2))):
                    continue
                data = dec(d[:128], d[128:]).astype(">u4").tobytes()
                found[sec] = data
            lib.CAPSUnlockTrack(img, cyl, head)
        for sec in range(11):
            if sec in found:
                o = (track * 11 + sec) * 512
                image[o:o + 512] = found[sec]
            else:
                bad.append((track, sec))

open(out, "wb").write(image)
tracks = sorted({t for t, _ in bad})
print(f"{1760 - len(bad)}/1760 sectors; tracks with missing sectors: {tracks}")
