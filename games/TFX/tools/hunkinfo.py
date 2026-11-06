#!/usr/bin/env python3
"""Print the hunk structure of AmigaOS load files and check relocations.

usage: hunkinfo.py FILE...
"""
import struct
import sys

NAMES = {0x3E7: "UNIT", 0x3E8: "NAME", 0x3E9: "CODE", 0x3EA: "DATA", 0x3EB: "BSS",
         0x3EC: "RELOC32", 0x3ED: "RELOC16", 0x3EE: "RELOC8", 0x3EF: "EXT",
         0x3F0: "SYMBOL", 0x3F1: "DEBUG", 0x3F2: "END", 0x3F3: "HEADER",
         0x3F7: "DREL32", 0x3F8: "DREL16", 0x3F9: "DREL8", 0x3FC: "RELOC32SHORT"}
MEM = {0: "any", 1: "chip", 2: "fast", 3: "ext"}


def parse(path):
    d = open(path, "rb").read()
    p = 0

    def L():
        nonlocal p
        v = struct.unpack_from(">L", d, p)[0]
        p += 4
        return v

    assert L() == 0x3F3, "not a load file"
    while L():
        k = L(); p += 4 * k  # resident library names
    n = L()
    first, last = L(), L()
    sizes = []
    for _ in range(last - first + 1):
        v = L()
        mem = v >> 30
        if mem == 3:
            L()
        sizes.append(((v & 0x3FFFFFFF) * 4, mem))
    print(f"{path}: {len(d)} bytes, {n} hunks")
    hunks = []
    cur = None
    problems = 0
    while p < len(d):
        t = L()
        tid = t & 0x3FFFFFFF
        name = NAMES.get(tid, hex(tid))
        if tid in (0x3E9, 0x3EA):
            nl = L()
            cur = {"type": name, "len": nl * 4, "off": p, "relocs": {}, "flags": t >> 30}
            hunks.append(cur)
            p += nl * 4
        elif tid == 0x3EB:
            cur = {"type": name, "len": L() * 4, "off": None, "relocs": {}, "flags": t >> 30}
            hunks.append(cur)
        elif tid == 0x3EC:
            while True:
                cnt = L()
                if not cnt:
                    break
                tgt = L()
                cur["relocs"].setdefault(tgt, []).extend(L() for _ in range(cnt))
        elif tid == 0x3FC:
            while True:
                cnt, = struct.unpack_from(">H", d, p); p += 2
                if not cnt:
                    break
                tgt, = struct.unpack_from(">H", d, p); p += 2
                offs = struct.unpack_from(f">{cnt}H", d, p); p += 2 * cnt
                cur["relocs"].setdefault(tgt, []).extend(offs)
            if p & 2:
                p += 2
        elif tid in (0x3F0, 0x3EF):
            while True:
                w = L()
                if not w:
                    break
                p += 4 * (w & 0xFFFFFF) + (4 if tid == 0x3F0 else 0)
                if tid == 0x3EF and (w >> 24) >= 0x80:
                    print("  (EXT import, not parsed)")
                    return
            cur.setdefault("symbols", True)
        elif tid == 0x3F1:
            k = L(); p += 4 * k
        elif tid == 0x3F2:
            pass
        else:
            print(f"  unknown hunk id {t:#x} at {p - 4:#x}")
            return
    for i, h in enumerate(hunks):
        alloc, mem = sizes[i]
        nrel = sum(len(v) for v in h["relocs"].values())
        print(f"  #{i:2d} {h['type']:4s} len={h['len']:#8x} alloc={alloc:#8x} mem={MEM[mem]:4s}"
              f" relocs={nrel:6d} sym={'y' if h.get('symbols') else '-'}")
        if h["len"] > alloc:
            print("     ! hunk data longer than header allocation"); problems += 1
        for tgt, offs in h["relocs"].items():
            if tgt >= len(hunks):
                print(f"     ! reloc to missing hunk {tgt}"); problems += 1; continue
            for o in offs:
                if o + 4 > h["len"]:
                    print(f"     ! reloc offset {o:#x} outside hunk"); problems += 1; break
                if h["off"] is not None:
                    v = struct.unpack_from(">L", d, h["off"] + o)[0]
                    if v >= sizes[tgt][0]:
                        print(f"     ! reloc at {o:#x} -> hunk {tgt} value {v:#x} beyond its size")
                        problems += 1
                        break
    print(f"  structural problems: {problems}")


for f in sys.argv[1:]:
    parse(f)
    print()
