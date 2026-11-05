#!/usr/bin/env python3
"""P13C1 native/oracle/CPU pixels and bounds. Functional models, never timers."""
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
from c2p_check import CPU, BASE, STACK, STOP, u, ck, P, I, Q, Z
from ocs_c2p import build, candidates, source, assemble
from ocs_reconstruct import ROOT, new_output
from ocs_display_check import Native, reference, visible, DESC, DESC2, PLANES, OTHER, DATA, SOURCE, WORK

SRC, DEST, DEST2 = 0x40000, 0x60000, 0x70000


class Candidate:
    def __init__(self, blob, sy, model):
        self.c = CPU(blob, model); self.sy = sy; self.blob = blob
        self.reads = []
        def read(handle, kind, address, size, value, data):
            self.reads.append((address, size))
        self.callback = C.CFUNCTYPE(None, P, I, Q, I, C.c_int64, P)(read)
        handle = Z()
        ck(u.uc_hook_add(self.c.h, C.byref(handle), 1 << 10, self.callback, None, 1, 0))
        self.lowest_stack = STACK

    def run(self, arm, w, h, pixels, index=0, alignment=0, flags=0, supervisor=False,
            pointers=None, expected_status=0):
        c = self.c; row = (w+15)//16*2; plane = row*(h+2)
        src, dst = (SRC+alignment, (DEST, DEST2)[index]+alignment) if pointers is None else pointers
        # Fixed guarded arenas allow even invalid dimensions/pointers to be tested
        # without constructing an invalid host allocation or reading through them.
        c.write(SRC-64, b'\x3c'*(64000+128)); c.write(SRC+alignment, pixels)
        c.write((DEST,DEST2)[index]-64, bytes([0xa5 if index == 0 else 0x5a])*(32320+128))
        before_planes = [c.read(base-64, 32320+128) for base in (DEST, DEST2)]
        before_source = c.read(SRC-64, 64000+128)
        c.reg(17, (0x2000 if supervisor else 0)|flags)
        for r in range(1, 17): c.reg(r, 0x12340000+r)
        c.reg(8, STACK); c.reg(1, src); c.reg(2, dst); c.reg(9, w); c.reg(10, h)
        c.write(STACK-544, b'\x96'*544); c.write(STACK, struct.pack('>I', STOP))
        before = [c.reg(r) for r in range(1, 17)]
        c.writes = []; self.reads = []
        ck(u.uc_emu_start(c.h, BASE+self.sy['ocs_c2p_'+arm], STOP, 10000000, 3000000))
        assert c.reg(18) == STOP, 'execution budget exceeded'
        after = [c.reg(r) for r in range(1, 17)]
        assert c.reg(9) == expected_status, ('status', arm, w, h, c.reg(9))
        assert all(before[r-1] == after[r-1] for r in range(1,17) if r not in (8,9)), 'register changed'
        assert c.reg(8) == STACK+4, 'stack not restored'
        assert c.read(STACK-544, 32) == b'\x96'*32, 'stack guard'
        assert c.read(SRC-64, 64000+128) == before_source, 'source modified'
        assert c.read(BASE, len(self.blob)) == self.blob, 'self-modifying code'
        visible_ranges = [(dst+n*plane+2*row, dst+n*plane+(h+1)*row) for n in range(4)] if expected_status == 0 else []
        stores = set()
        for addr, count in c.writes:
            if STACK-512 <= addr and addr+count <= STACK:
                self.lowest_stack = min(self.lowest_stack, addr); continue
            assert any(lo <= addr and addr+count <= hi for lo,hi in visible_ranges), ('unexpected write',hex(addr),count)
            stores.add(count)
        if expected_status == 0:
            assert stores == ({2} if arm == 'word' else {4}), 'wrong destination store width'
        for addr, count in self.reads:
            assert (STACK-512 <= addr and addr+count <= STACK+4 or
                    expected_status == 0 and src <= addr and addr+count <= src+w*(h-1)), ('unexpected read',hex(addr),count)
        want = bytearray(before_planes[index])
        if expected_status == 0:
            packed = reference(pixels, w, h)
            for n in range(4):
                start = 64+alignment+n*plane+2*row
                want[start:start+row*(h-1)] = packed[n*row*(h-1):(n+1)*row*(h-1)]
        actual = c.read((DEST,DEST2)[index]-64, 32320+128)
        assert actual == want, ('pixels/padding mismatch', arm,w,h,index,alignment)
        assert c.read((DEST2,DEST)[index]-64, 32320+128) == before_planes[1-index], 'opposite destination changed'
        return b''.join(c.read(dst+n*plane+2*row, row*(h-1)) for n in range(4)) if expected_status == 0 else b''

    def close(self): self.c.close()


def native_convert(c, descriptor, base, other):
    before_source = c.read(SOURCE-2*c.width, c.width*(c.height+4))
    before_other = c.read(other,c.size)
    c.convert(descriptor)
    assert c.read(other,c.size) == before_other, 'native opposite destination changed'
    assert c.read(SOURCE-2*c.width, c.width*(c.height+4)) == before_source, 'native source changed'
    for region in (PLANES,OTHER,WORK):
        assert c.read(region-64,64) == b'\x5a'*64 and c.read(region+c.size,64) == b'\x5a'*64, 'native allocation overrun'
    return visible(c,base)


def fixtures(w,h):
    rng = random.Random((w << 16)+h)
    return {'pairs':bytes(((i & 15)<<4)|((i//16+3)&15) for i in range(w*h)),
            'random':bytes(rng.randrange(256) for _ in range(w*h)),
            'white':b'\xff'*(w*h)}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    a = p.parse_args(); inputs = candidates(); out = new_output(a.output); out.mkdir(parents=True)
    blob, sy = build(out, inputs)
    native = Native(ROOT/'tmp/game/WingCommander/data/Wing.english')
    runners = [(arm,model,Candidate(blob,sy,model)) for arm,models in
               (('word',(1,2,4)),('long',(2,4))) for model in models]
    records = []; cpu_count = native_count = 0
    try:
        # Native display view rectangles: all widths 320, heights 200/166/128.
        # Whole executable hash is checked by Native before reading these data.
        views = []
        for offset,expected in ((0xc4,(0,0,319,199)),(0xe4,(0,0,319,165)),(0xf4,(0,0,319,127))):
            rect = struct.unpack('>4h',native.read(DATA+offset,8))
            assert rect == expected, 'native view bounds changed'
            views.append((rect[2]-rect[0]+1,rect[3]-rect[1]+1))
        for w,h in views+[(w,16) for w in range(32,321,32)]+[(64,18)]:
            for label,pixels in fixtures(w,h).items():
                native.setup(w,h,pixels)
                expected = reference(pixels,w,h)
                for index,desc,base in ((0,DESC,PLANES),(1,DESC2,OTHER)):
                    actual_native = native_convert(native,desc,base,OTHER if index == 0 else PLANES)
                    native_count += 1
                    assert actual_native == expected, ('native oracle',w,h,label,index)
                    for arm,model,c in runners:
                        actual = c.run(arm,w,h,pixels,index,alignment=2*index)
                        assert actual == visible(native,base), 'CPU/native mismatch'
                        cpu_count += 1
                records.append(dict(width=w,height=h,fixture=label,sha256=hashlib.sha256(expected).hexdigest()))
            print('passed native/CPU geometry', w,h, flush=True)
        # 16-pixel-but-not-32 widths must request native before changing memory.
        # Execute the native route as well: fallback is not a silent skipped frame.
        fallback_count = 0
        for w in range(16,321,32):
            pixels = fixtures(w,16)['random']; native.setup(w,16,pixels)
            assert native_convert(native,DESC,PLANES,OTHER) == reference(pixels,w,16)
            native_count += 1
            for arm,model,c in runners:
                c.run(arm,w,16,pixels,expected_status=1); fallback_count += 1
        invalids = [(w,h) for w,h in ((0,16),(15,16),(17,16),(321,16),(65568,16),(32,0),
                    (32,15),(32,17),(32,199),(32,201),(32,65552),(0xffffffff,16))]
        invalid_count = 0
        for arm,model,c in runners:
            for w,h in invalids:
                c.run(arm,w,h,b'',expected_status=2); invalid_count += 1
            for ptrs in ((0,DEST),(SRC,0),(SRC+1,DEST),(SRC,DEST+1)):
                c.run(arm,32,16,bytes(512),pointers=ptrs,expected_status=2); invalid_count += 1
            c.run('native',32,16,bytes(512),expected_status=1)
        # All admitted even heights and both row parities: no accidental 166/200
        # specialisation. This is scalar-oracle coverage, not native geometry proof.
        for h in range(16,201,2):
            for arm,model,c in (runners[0],runners[3]):
                c.run(arm,32,h,fixtures(32,h)['random'],index=h%4//2)
                cpu_count += 1
        # Flags are explicitly clobbered; all live registers and both user/super
        # execution modes must work for every incoming CCR combination.
        abi_count = 0
        for arm,model,c in runners:
            for supervisor in (False,True):
                for flags in range(32):
                    c.run(arm,32,16,fixtures(32,16)['pairs'],flags=flags,supervisor=supervisor)
                    abi_count += 1
        # Negative controls mutate generated adapters, never shared upstream files.
        bad = []
        good = source(inputs)
        for name,old,new in (
                ('low_nibble_only','or.l    d1,d0','move.l -4(a0),d0\n        andi.l #$0f0f0f0f,d0'),
                ('wrong_row_parity','exg     d2,d3','nop'),
                ('missing_edge','clr.b   1(a5)','nop'),
                ('wrong_leading_rows','addq.w  #2,d3','addq.w  #1,d3')):
            assert old in good
            altered, symbols = assemble(out, name, good.replace(old,new))
            c = Candidate(altered,symbols,1)
            try:
                try: c.run('word',32,16,fixtures(32,16)['pairs'])
                except AssertionError: bad.append(name)
                else: raise AssertionError('mutation escaped: '+name)
            finally: c.close()
        assert len(bad) == 4
        # Pin verification rejects changed local inputs without overwriting them.
        pinned = out/'changed-inputs'
        for name,digest,text in inputs:
            path = pinned/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text)
        rejected_pins = []
        for name,digest,text in inputs:
            path = pinned/name; changed = text+'\n; mutation\n'; path.write_text(changed)
            try: candidates(pinned)
            except ValueError: rejected_pins.append(name)
            else: raise AssertionError('changed input accepted')
            assert path.read_text() == changed, 'changed input overwritten'
            path.write_text(text)
        assert len(rejected_pins) == 2
        report = dict(passed=True,scope='isolated native 68000/blitter and CPU-model correctness',
                      native_conversions=native_count,cpu_conversions=cpu_count,abi_cases=abi_count,
                      native_fallback_cases=fallback_count,invalid_cases=invalid_count,mutations_rejected=bad,
                      native_views=views,rejected_pins=rejected_pins,fixtures=records,stack_bytes=max(STACK-c.lowest_stack for _,_,c in runners),
                      models=[dict(arm=arm,model=model) for arm,model,_ in runners],
                      live_hooks=False,performance_measured=False)
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('P13C1 gate passed', native_count,cpu_count,abi_count)
    finally:
        native.close()
        for _,_,c in runners: c.close()


if __name__ == '__main__': main()
