#!/usr/bin/env python3
"""Build an explicitly selected variant in tmp/; native reconstructions prove identity.
The repository contains offsets and conversion rules, never the derived assembly.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
from variants import cd32 as VARIANT
from shared_cpu import unit
import capstone
from render_source import source as render_source, flight_source
from timing_source import source as timing_source

ROOT = Path(__file__).resolve().parents[1]
SLAVE_SHA = VARIANT.SLAVE_SHA
# Code islands established from entry, ROM/game patch destinations, filesystem
# dispatch table, callback pointers and branches. Everything else is data.
CODE = [(0,4), (0x34,0x7a), (0x4fa,0x4fe), (0x500,0x75a),
        (0x768,0x87c), (0x8de,0x8f0), (0x8f8,0x9ac), (0xa22,0x1130), (0x11bc,0x11c8),
        (0x13f0,0x14f8), (0x1524,0x15ae), (0x1696,0x17ee),
        (0x17f6,0x1cde), (0x1da4,0x1dc6)]


def cd32_main(argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    modes = p.add_mutually_exclusive_group()
    modes.add_argument('--release',action='store_true',help='public options: language and enhanced/Psygore modes')
    modes.add_argument('--timing', action='store_true', help='experimental CUSTOM1=3 English hybrid timing adapter')
    p.add_argument('--frame-stats', action='store_true', help='diagnostic frame-part recorder saved as framestats.bin; requires --timing or --release')
    modes.add_argument('--render', action='store_true', help='experimental CUSTOM1=2 English rendering adapter')
    modes.add_argument('--render-control', action='store_true', help='same-size original converter with the same gated WHDLoad cache policy')
    modes.add_argument('--verify', action='store_true', help='build the CUSTOM1=2 diagnostic seam')
    modes.add_argument('--verify-control', action='store_true', help='original code with the same unused diagnostic tail/size')
    modes.add_argument('--ceiling',choices=['control','c2p','drawing-control','drawing','drawing-bitmap','drawing-clear'],help='VERIFY-only equal-size rendering ceiling fixture; never a release build')
    modes.add_argument('--cache-audit', action='store_true', help='VERIFY-only terminating hardware CACR audit')
    p.add_argument('--flight-verify',action='store_true',help='compare flight delta c2p against original on every picture')
    p.add_argument('--comparison-control',action='store_true',help='D4 diagnostic old comparison loop, same size')
    p.add_argument('--flight-control',action='store_true',help='same-size flight full-conversion control')
    p.add_argument('--timing-verify',action='store_true',help='include diagnostic render schedules; requires --timing')
    p.add_argument('--render-family', choices=('auto','030','040'), default='auto', help='diagnostic converter-family override')
    p.add_argument('--render-verify', action='store_true', help='native original/replacement twin on every conversion; requires --render')
    p.add_argument('--input', default=VARIANT.SLAVE)
    p.add_argument('--c2p-experiment',choices=('control','block040','full-original','full030','full040'),help='D5 diagnostic equal-layout converter comparison; release only')
    a = p.parse_args(argv)
    if a.c2p_experiment and not a.release:p.error('--c2p-experiment requires --release')
    if a.release:
        if a.timing_verify or a.flight_verify or a.flight_control or a.render_verify or a.render_family!='auto':
            p.error('public-option build supports frame-stats, comparison-control and c2p-experiment diagnostics')
        a.timing=True
    if a.comparison_control and not a.timing:p.error('comparison control requires --timing or --release')
    if (a.flight_verify or a.flight_control) and not a.timing:p.error('flight diagnostics require --timing')
    if a.frame_stats and not a.timing:p.error('--frame-stats requires --timing')
    if a.timing_verify and not a.timing: p.error('--timing-verify requires --timing')
    if a.render_family!='auto' and not a.render: p.error('--render-family requires --render')
    if a.render_verify and not a.render: p.error('--render-verify requires --render')
    out = (ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('choose a new output directory below tmp/')
    original = (ROOT/a.input).read_bytes()
    if hashlib.sha256(original).hexdigest() != SLAVE_SHA:
        raise ValueError('unsupported/changed slave; nothing overwritten')
    code = original[0x20:-4]
    assert len(code) == 0x1e0c
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_020)
    decoded = {}
    for start,end in CODE:
        pos = start
        while pos < end:
            i = next(md.disasm(code[pos:end], pos, count=1))
            assert i.mnemonic != 'dc.w' and i.size and pos+i.size <= end, hex(pos)
            mnemonic, operands = i.mnemonic, i.op_str
            if mnemonic.split(".")[0] in ("btst","bset","bclr","bchg"):
                mnemonic = mnemonic.split(".")[0]
            # MOVEM has an extension word before its PC-relative operand;
            # Capstone 5 reports a target two bytes short.
            if mnemonic.startswith('movem'):
                operands = re.sub(r'\$([0-9a-f]+)(?=\(pc)',
                                  lambda m: '$%x' % (int(m[1],16)+2), operands)
            # Capstone sign-extends a negative 16-bit PC base displacement as
            # unsigned in the 020 memory-indirect form (entry S:72).
            operands = re.sub(r'\$([0-9a-f]+)(?=, pc)',
                              lambda m: '$%x' % (int(m[1],16)&0xffff), operands)
            operands = re.sub(r'\$([0-9a-f]+)(?=\(pc|, pc)',
                              lambda m: 'slave+$'+m[1], operands)
            if mnemonic.startswith('b') and mnemonic.split('.')[0] not in ('btst','bset','bclr','bchg'):
                operands = re.sub(r'^\$([0-9a-f]+)$', r'slave+$\1', operands)
            if mnemonic.startswith('db'):
                operands = re.sub(r'\$([0-9a-f]+)$', r'slave+$\1', operands)
            # Vasm's explicit absolute size syntax.
            operands = re.sub(r'\$([0-9a-f]+)\.(w|l)', lambda m: '('+str(int(m[1],16)-(65536 if m[2]=='w' and int(m[1],16)>=32768 else 0))+').'+m[2], operands)
            if mnemonic == 'moveq':
                operands = re.sub(r'#\$([0-9a-f]+)', lambda m: '#'+str((int(m[1],16)+128)%256-128), operands)
            decoded[pos] = (i.size, mnemonic+' '+operands)
            pos += i.size
    lines = ['; Generated from the SHA-256 pinned original; keep in ignored tmp/.',
             '\torg 0', 'slave:']
    pos = 0
    while pos < len(code):
        lines += [f'\tifne *-slave-${pos:x}', '\tfail "offset drift"', '\tendif', f'S_{pos:04x}:']
        if pos in decoded:
            size, source = decoded[pos]
            if a.release and pos==0x1422:
                lines.append('\tbsr.w release_setcpu')
            elif a.timing and pos==0x178a:
                lines.append('\tbra.w timing_converter_entry')
            elif (a.render and pos==0x178a) or ((a.render or a.render_control) and pos==0x1422):
                lines.append('\t'+('bra.w render_entry' if pos==0x178a else 'bsr.w render_setcpu'))
            elif pos == 0x1422 and a.cache_audit:
                lines.append('\tbsr.w cache_audit')
            elif a.ceiling == 'c2p' and pos in (0x17f6,0x195e,0x1ac6):
                # Return from the leaf converter call. The wrapper still saves
                # registers, runs the original limiter and publishes normally.
                lines.append('\trts')
                if size > 2:
                    lines.append('\tdc.b '+','.join(f'${b:02x}' for b in code[pos+2:pos+size]))
            elif pos == 0x14da and a.ceiling and a.ceiling.startswith('drawing'):
                lines.append('\tbsr.w drawing_patchseg')
            elif pos == 0x14da and a.timing:
                lines.append('\tbsr.w timing_patchseg')
            elif pos == 0x14da and a.verify:
                lines.append('\tbsr.w verify_patchseg')
            else:
                lines.append('\t'+source)
        else:
            size = min(16, len(code)-pos)
            while any(pos < x < pos+size for x in decoded):
                size -= 1
            lines.append('\tdc.b '+','.join(f'${b:02x}' for b in code[pos:pos+size]))
        pos += size
    if a.render or a.render_control:
        lines.append('RENDER_VERIFY equ '+str(int(a.render_verify)))
        lines.append('RENDER_FAMILY equ '+str({'auto':0,'030':30,'040':40}[a.render_family]))
        lines.append(render_source(ROOT, variant="cd32"))
    if a.release:
        lines.append((ROOT/'whdload/release.s').read_text())
    if a.timing:
        lines.append('TIMING_VERIFY equ '+str(int(a.timing_verify)))
        lines.append('FRAME_STATS equ '+str(int(a.frame_stats)))
        lines.append('BUFFERED equ '+str(int(a.release)))
        lines.append(timing_source(ROOT, buffered=a.release, variant="cd32"))
        if a.release:lines.append(unit(ROOT, 'release_buffer', VARIANT.CPU))
        if a.frame_stats:lines.append(unit(ROOT, 'frame_stats', VARIANT.CPU))
        flight=flight_source(ROOT,a.flight_verify,a.flight_control,a.comparison_control,a.c2p_experiment, variant="cd32")
        if a.release:
            begin=flight.index('        move.l  slave+$1e04(pc),d7')
            end=flight.index('.work:',begin)
            flight=flight[:begin]+'        bsr.w release_convert_wait\n'+flight[end:]
            begin=flight.index('        ; Same safe display-end')
            end=flight.index('        movem.l (sp)+,d0-a6',begin)
            flight=flight[:begin]+flight[end:]
            flight=flight.replace('flight_render_original:\n        bra.w   slave+$178e',
                'flight_render_original:\n        movem.l (sp)+,d0-a6\n        bra.w render_entry')
        lines.append(flight)
    if a.release:
        renderer=render_source(ROOT, variant="cd32").replace('cmpi.l  #2,d7','cmpi.l  #3,d7').replace('cmpi.l  #2,d2','cmpi.l  #3,d2')
        begin=renderer.index('        move.l  slave+$1e04(pc),d7')
        end=renderer.index('.convert:',begin)
        renderer=renderer[:begin]+'        bsr.w   release_limit\n'+renderer[end:]
        renderer=renderer.replace('render_wait:\n','render_wait:\n        tst.w timing_active(pc)\n        bne.w render_wait_done\n        tst.w intro_active(pc)\n        bne.w render_wait_done\n')
        lines += ['RENDER_VERIFY equ 0','RENDER_FAMILY equ 0',renderer]
    if a.verify or a.verify_control:
        lines.append((ROOT/'whdload/verify.s').read_text())
    if a.ceiling and a.ceiling.startswith('drawing'):
        bitmap='$4e75' if a.ceiling in ('drawing','drawing-bitmap') else '$48e7'
        clear='$4e75' if a.ceiling in ('drawing','drawing-clear') else '$48e7'
        lines.append((ROOT/'whdload/drawing_ceiling.s').read_text().replace('BITMAP_OPCODE',bitmap).replace('CLEAR_OPCODE',clear))
    if a.cache_audit:
        lines.append((ROOT/'whdload/cache_audit.s').read_text())
    out.mkdir(parents=True)
    source = out/'WingCommanderCD32.s'
    source.write_text('\n'.join(lines)+'\n')
    binary = out/'payload.bin'
    subprocess.run([os.environ['VASM'], '-m68020','-spaces','-no-opt','-Fbin','-L',str(out/'slave.lst'),'-o',str(binary),str(source)],check=True)
    built = binary.read_bytes()
    if a.render or a.render_control:
        expected=bytearray(code)
        for offset in ((0x1422,0x178a) if a.render else (0x1422,)): expected[offset:offset+4]=built[offset:offset+4]
        if built[:len(code)] != expected: raise ValueError('render build differs outside declared seams')
    if a.cache_audit:
        if built[:0x1422] != code[:0x1422] or built[0x1426:len(code)] != code[0x1426:]:
            raise ValueError('cache audit changed bytes outside the SetCPU detour')
        built = built[:0xc]+struct.pack('>H',18)+built[0xe:]
    if a.ceiling:
        expected=bytearray(code)
        if a.ceiling=='c2p':
            for offset in (0x17f6,0x195e,0x1ac6):expected[offset:offset+2]=bytes.fromhex('4e75')
        if a.ceiling and a.ceiling.startswith('drawing'):
            expected[0x14da:0x14de]=struct.pack('>Hh',0x6100,len(code)-(0x14da+2))
            if len(built)<=len(code) or len(built)%4 or built[:len(code)]!=expected:
                raise ValueError('drawing fixture changed original code outside the PatchSeg detour')
        elif built!=expected:raise ValueError('ceiling fixture differs outside declared converter entry words')
    if not (a.timing or a.render or a.render_control or a.verify or a.cache_audit or a.ceiling) and built[:len(code)] != code:
        differences = [hex(i) for i,(x,y) in enumerate(zip(built,code)) if x != y]
        raise ValueError(f'reassembly differs: size {len(built)}; first offsets {differences[:20]}')
    if a.verify or a.timing:
        # Only declared PatchSeg and (timing mode) c2p entry seams may change.
        expected=bytearray(code)
        for off in ((0x1422,0x14da,0x178a) if a.release else (0x14da,0x178a) if a.timing else (0x14da,)):
            expected[off:off+4]=built[off:off+4]
        if built[:len(code)] != expected:
            raise ValueError('VERIFY changed bytes outside its declared detour')
    if a.release:
        symbols={name:int(off,16) for off,name in re.findall(r'^([0-9A-F]{8}) (\S+)$',(out/'slave.lst').read_text(),re.M)}
        updated=bytearray(built)
        for offset,label in ((0x24,'release_name'),(0x28,'release_info'),(0x32,'release_config')):
            if symbols[label]>=0x8000:raise ValueError('header string outside signed offset range')
            struct.pack_into('>H',updated,offset,symbols[label])
        built=bytes(updated)
        binary.write_bytes(built)
    # Standard one-code-hunk container; no original byte blob is embedded.
    header = struct.pack('>8I',0x3f3,0,1,0,0,len(built)//4,0x3e9,len(built)//4)
    result = header+built+struct.pack('>I',0x3f2)
    if not (a.timing or a.render or a.render_control or a.verify or a.verify_control or a.cache_audit or a.ceiling):
        assert result == original
    (out/'WingCommanderCD32.Slave').write_bytes(result)
    report = {'variant': 'cd32', 'sha256': hashlib.sha256(result).hexdigest(), 'bytes':len(result),
              'instructions':len(decoded), 'instruction_bytes':sum(v[0] for v in decoded.values()),
              'code_ranges':CODE, 'byte_identical':result == original, 'release':a.release, 'buffered':a.release, 'frame_records':8192 if a.release and a.frame_stats else 16384 if a.frame_stats else 0, 'version':'2.0b' if a.release else None, 'comparison_control':a.comparison_control, 'flight_verify':a.flight_verify, 'c2p_experiment':a.c2p_experiment, 'flight_control':a.flight_control or bool(a.c2p_experiment and a.c2p_experiment.startswith('full')), 'timing':a.timing, 'timing_verify':a.timing_verify, 'frame_stats':a.frame_stats, 'render':a.render, 'render_control':a.render_control, 'render_verify':a.render_verify, 'render_family':a.render_family, 'ceiling':a.ceiling, 'verify_only':bool(a.c2p_experiment or a.ceiling or a.timing_verify or a.frame_stats or a.flight_verify or a.flight_control or a.comparison_control), 'cache_audit':a.cache_audit, 'verify':a.verify, 'verify_control':a.verify_control}
    if a.ceiling and a.ceiling.startswith('drawing'):
        report.update(drawing_entries=[0x2efe8,0x31cd6],drawing_word=len(built)-4,drawing_installs=len(built)-8)
    (out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

def main():
    select = argparse.ArgumentParser(description='Build a selected variant; outputs stay in tmp/.', add_help=False)
    select.add_argument('--variant', choices=('cd32', 'ocs'), required=True)
    args, remaining = select.parse_known_args()
    if args.variant == 'ocs':
        from ocs_reconstruct import main as ocs_main
        ocs_main(remaining)
    else:
        cd32_main(remaining)


if __name__ == '__main__':
    main()
