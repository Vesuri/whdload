#!/usr/bin/env python3
"""Compare reloc tables/code of hunk files and count implausible relocations.

usage: relocdiff.py REF FILE...
"""
import struct
import sys


def load(path):
    d = open(path, "rb").read()
    p = 0

    def L():
        nonlocal p
        v = struct.unpack_from(">L", d, p)[0]
        p += 4
        return v

    assert L() == 0x3F3
    while L():
        k = L(); p += 4 * k
    L(); first, last = L(), L()
    sizes = [(L() & 0x3FFFFFFF) * 4 for _ in range(last - first + 1)]
    hunks = []
    while p < len(d):
        t = L() & 0x3FFFFFFF
        if t in (0x3E9, 0x3EA):
            n = L(); hunks.append({"data": d[p:p + 4 * n], "relocs": {}}); p += 4 * n
        elif t == 0x3EB:
            hunks.append({"data": None, "len": L() * 4, "relocs": {}})
        elif t == 0x3EC:
            while True:
                c = L()
                if not c:
                    break
                tg = L()
                hunks[-1]["relocs"].setdefault(tg, []).extend(L() for _ in range(c))
        elif t == 0x3F1:
            k = L(); p += 4 * k
        elif t == 0x3F2:
            pass
        else:
            raise SystemExit(f"{path}: unhandled hunk {t:#x}")
    return sizes, hunks


ref_sizes, ref = load(sys.argv[1])
for f in sys.argv[2:]:
    sizes, hs = load(f)
    print(f"== {f} vs {sys.argv[1]}")
    for i, h in enumerate(hs):
        same = h["relocs"] == ref[i]["relocs"] if i < len(ref) else None
        bad = total = 0
        for tg, offs in h["relocs"].items():
            for o in offs:
                total += 1
                v = struct.unpack_from(">L", h["data"], o)[0]
                if v >= sizes[tg]:
                    bad += 1
        diff = "-"
        if h["data"] is not None and i < len(ref) and ref[i]["data"] is not None:
            a, b = h["data"], ref[i]["data"]
            m = min(len(a), len(b))
            diff = sum(1 for k in range(m) if a[k] != b[k]) + abs(len(a) - len(b))
        print(f"  hunk {i}: relocs={total} implausible={bad} reloc-table-identical={same} bytes-differing={diff}")
