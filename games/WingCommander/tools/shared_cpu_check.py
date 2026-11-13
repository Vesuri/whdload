#!/usr/bin/env python3
"""P13B2 base-ISA assembly and executed CPU-only boundary checks (no speed claim)."""
import argparse
import json
import os
import random
import re
import struct
import subprocess
from pathlib import Path
from c2p_check import CPU, BASE, STACK, STOP, u, ck
from shared_cpu import UNITS, select, unit, preamble
from german_map import english
from variants import cd32, assembly_definitions

ROOT = Path(__file__).resolve().parents[1]


def assemble(out, name, source, cpu):
    path = out / (name + '.s')
    path.write_text(source)
    cmd = [os.environ['VASM'], '-m'+cpu, '-spaces', '-no-opt', '-Fbin',
           '-L', str(out/(name+'.lst')), '-o', str(out/(name+'.bin')), str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode: raise ValueError(result.stdout + result.stderr)
    blob = (out/(name+'.bin')).read_bytes()
    symbols = {n:int(v,16) for v,n in re.findall(r'^([0-9A-F]{8}) (\S+)$', (out/(name+'.lst')).read_text(), re.M)}
    return blob, symbols


def externals(source):
    """Explicit fixture-only link placeholders; never passed to a slave build."""
    defined = set(re.findall(r'^([\w]+)\s*(?::|=|equ\b|macro\b)', source, re.M))
    refs = set()
    for line in source.splitlines():
        line = re.sub(r"'[^']*'", '', line.split(';')[0])
        if not line.startswith((' ', '\t')): continue
        words = line.strip().split(None,1)
        if len(words)<2: continue
        for token in re.findall(r'(?<![\w.$])\b[A-Za-z_]\w*\b',words[1]):
            if token.lower() not in {'sp','pc','ccr','sr','w','l','b','d0','d1','d2','d3','d4','d5','d6','d7','a0','a1','a2','a3','a4','a5','a6'}:
                refs.add(token)
    return sorted(refs-defined)


def fstat_macro():
    src=(ROOT/'src/timing.s').read_text()
    start=src.index('FSTAT   macro')
    return src[start:src.index('        endm',start)+len('        endm')]+ '\n'


def assembly_gate(out):
    assert {p.stem for p in (ROOT/'src').glob('timing*.s')} <= set(UNITS)
    rows=[]
    for buffered,stats,verify in ((0,0,0),(0,1,1),(1,0,0),(1,1,0)):
        for name in UNITS:
            src = english(unit(ROOT,name,'68000'))
            header = assembly_definitions(cd32) + f'BUFFERED equ {buffered}\nFRAME_STATS equ {stats}\nTIMING_VERIFY equ {verify}\n'
            if name != 'timing':
                header += fstat_macro()
            unresolved = externals(header+src)
            # Placeholder boundaries only test each whole owned unit's ISA.
            # The actual OCS linker/native ABI is deliberately not fabricated.
            header += ''.join(f'{n} equ 0\n' for n in unresolved)
            blob,_ = assemble(out,f'{name}-{buffered}{stats}{verify}',header+preamble(ROOT,'68000')+src,'68000')
            rows.append(dict(unit=name,buffered=buffered,stats=stats,verify=verify,bytes=len(blob),fixture_externals=unresolved))
    return rows


def invoke(c, offset, regs=None, flags=0, supervisor=False):
    c.reg(17,(0x2000 if supervisor else 0)|flags)
    for r in range(1,17): c.reg(r,0x34560000+r)
    c.reg(8,STACK)
    for r,v in (regs or {}).items(): c.reg(r,v & 0xffffffff)
    c.write(STACK,struct.pack('>I',STOP))
    ck(u.uc_emu_start(c.h,BASE+offset,STOP,1000000,100000))
    assert c.reg(18)==STOP and c.reg(8)==STACK+4


def trunc(n,d): return (abs(n)//d)*(-1 if n<0 else 1)


def arithmetic_gate(out):
    scene=english((ROOT/'src/timing_scene.s').read_text())
    trans=english((ROOT/'src/timing_translation.s').read_text())
    src=scene[scene.index('timing_scene_scale:'):scene.index('timing_scene_begin:')]
    src+=trans[trans.index('translation_fraction:'):trans.index('translation_field:')]
    src+=(ROOT/'src/timing_clock.s').read_text()
    rng=random.Random(0x13b2)
    values=[-2**31,-2**31+1,-65536,-32769,-1,0,1,32767,65535,2**31-1]+[rng.randrange(-2**31,2**31) for _ in range(40)]
    rows=[]
    for cpu,models in (('68000',(1,2,4)),('68020',(2,4))):
        blob,sy=assemble(out,'math-'+cpu,preamble(ROOT,cpu)+select(src,cpu),cpu)
        for model in models:
            c=CPU(blob,model);count=0
            for hz in (50,60):
                for value in values:
                    for fraction in (0,1,hz//2,hz-1,hz,hz+10,hz+20):
                        invoke(c,sy['timing_scene_scale'],{9:value,15:fraction,16:hz})
                        assert c.reg(9)==trunc(value*fraction,hz)&0xffffffff,(cpu,model,hz,value,fraction,c.reg(9))
                        assert all(c.reg(r)==0x34560000+r for r in (1,2,3,4,5,6,7,12,13,14))
                        assert c.reg(15)==fraction and c.reg(16)==hz
                        count+=1
                    for rem in (-hz+1,-1,0,1,hz-1):
                        c.write(0x30000,struct.pack('>i',rem))
                        invoke(c,sy['translation_fraction'],{1:0x30000,9:value,16:hz})
                        expected=trunc(value*10+rem,hz)
                        assert c.reg(9)==expected&0xffffffff
                        assert struct.unpack('>i',c.read(0x30000,4))[0]==value*10+rem-expected*hz
                        assert c.reg(1)==0x30004 and c.reg(16)==hz
                        assert all(c.reg(r)==0x34560000+r for r in (2,3,4,5,6,7,13,14,15))
                        count+=1
            # Use the existing independent scheduler ledger, now on the selected M68000 model.
            from timing_clock_check import invoke as clock_invoke, STATE
            clock=c.read(BASE+sy['timing_advance'],len(blob)-sy['timing_advance'])
            q=CPU(clock,model)
            for hz in (50,60):
                for steps in ((1,),(2,3),(7,11),(1,9,3,2)):
                    q.write(STATE,bytes(28));origin=0xfffffff0
                    assert clock_invoke(q,origin,hz,1)[0]==0
                    fields=issued=0
                    for i in range(hz*2):
                        fields+=steps[i%len(steps)];n,s=clock_invoke(q,origin+fields,hz,1);issued+=n
                        assert issued==fields*10//hz and s[1]==fields*10%hz and s[4]==0
                        count+=1
                    clock_invoke(q,origin+fields,hz,0)
                    assert clock_invoke(q,origin+fields+10000,hz,1)[0]==0
                for elapsed in (hz,hz+1,0x10000,0x7fffffff,0xffffffff):
                    q.write(STATE,bytes(28));clock_invoke(q,0,hz,1)
                    n,s=clock_invoke(q,elapsed,hz,1)
                    assert n==(4 if elapsed==hz else 0)
                    assert s[4]==((6*hz) if elapsed==hz else (elapsed*10)&0xffffffff)
            q.close();c.close()
            rows.append(dict(isa=cpu,model=model,cases=count))
    return rows


def operand_flag_gate(out):
    snippets = [
        'move.w ccr,-(sp)\n        move.w (sp)+,ccr',
        'move.w $1700(a4,d4.w*2),d1',
        'move.w $24de(a4,d0.w*2),$255e(a4,d0.w*2)',
        'lea (a4,d0.w*4),a3',
        'move.l d0,16(a0,d1.l*4)',
        'cmpi.w #11,(a0,d4.w*2)',
        'sub.w (a0,d4.w*2),d0',
        'tst.w data(pc)',
        'cmpi.w #7,data(pc)',
        'jsr $21000(a6)',
        'jmp $21000(a6)',
        'bra.l capture',
    ]
    rows=[]
    targets={}
    for index,snippet in enumerate(snippets):
        src='entry:\n        '+snippet+'\ncapture:\n        move.w ccr,-(sp)\n        move.w (sp)+,$38000\n        rts\ndata: dc.w 7\n'
        builds={}
        for cpu in ('68000','68020'):
            builds[cpu]=assemble(out,f'operands-{index}-{cpu}',preamble(ROOT,cpu)+select(src,cpu),cpu)[0]
        count=0
        for supervisor in (False,True):
          for flags in range(32):
           for slot in (3,0xfffffffe):
            expected=None
            for isa,model in (('68020',2),('68020',4),('68000',1),('68000',2),('68000',4)):
                c=CPU(builds[isa],model)
                # Synthetic callee checks the incoming flags and argument stack.
                target='callee:\n        move.w ccr,-(sp)\n        move.w (sp)+,$38002\n        move.l 4(sp),$38004\n        rts\n'
                # Assembled once per ISA below and reused across flag combinations.
                if isa not in targets:
                    targets[isa]=assemble(out,'callee-'+isa,preamble(ROOT,isa)+select(target,isa),isa)[0]
                c.write(BASE+0x21000,targets[isa])
                c.write(0x40000,bytes(range(256))*768)
                c.write(STACK+4,struct.pack('>I',0xcafebabe))
                regs={1:0x50000,2:0x58000,3:0x60000,4:0x68000,5:0x50000,6:0x60000,7:BASE,9:slot,10:3,13:slot}
                invoke(c,0,regs,flags,supervisor)
                result=([c.reg(r) for r in range(1,17)],c.read(0x38000,8),c.read(0x40000,0x30000))
                if expected is None:expected=result
                else:assert result==expected,(index,isa,model,flags,supervisor,slot)
                if index in (9,10):
                    assert struct.unpack('>H',c.read(0x38002,2))[0]&31==flags
                    assert struct.unpack('>I',c.read(0x38004,4))[0]==(STOP if index==9 else 0xcafebabe)
                c.close();count+=1
        rows.append(dict(instruction=snippet,cases=count))
    return rows


def linked_fixture(out,name,cpu,stats=0):
    src=english(unit(ROOT,name,cpu))
    header=assembly_definitions(cd32)+f'BUFFERED equ 1\nFRAME_STATS equ {stats}\nTIMING_VERIFY equ 0\n'
    # Data/callback placeholders are only for isolated execution, explicitly
    # distinct from the real game or any OCS hook/ABI implementation.
    header+=fstat_macro()
    names=externals(header+src)
    tail=''.join(f'\n{n}: dcb.b 128,0\n' for n in names)
    return assemble(out,f'linked-{name}-{cpu}',header+preamble(ROOT,cpu)+src+tail,cpu)


def wrappers_gate(out):
    from frame_stats_check import check as recorder_check
    rows=[]
    for isa,models in (('68000',(1,2,4)),('68020',(2,4))):
        blob,sy=linked_fixture(out,'frame_stats',isa,1)
        for model in models:
            for samples,expected in (([8,8],8),([255,256,256,256],256)):
                recorder_check(blob,sy,model,samples,expected)
                rows.append(dict(unit='frame_stat',isa=isa,model=model,race=len(samples)>2))
        blob,sy=linked_fixture(out,'release_buffer',isa)
        for model in models:
          c=CPU(blob,model);ck(u.uc_mem_map(c.h,0xdff000,4096,7))
          for flags in range(32):
           for case in ('idle','future','late','locked','publish'):
            def put(n,fmt,value):c.write(BASE+sy[n],struct.pack('>'+fmt,value))
            put('release_pending','H',case!='idle')
            put('release_pending_time','I',101 if case=='future' else 100)
            put('timing_data','I',0x40000);put('timing_game','I',BASE)
            put('release_pending_a4','I',0x47ffe);put('release_pending_index','H',1)
            put('release_pending_plane','I',0x60000);put('release_front','I',0)
            put('release_late','I',0)
            c.write(0x47f02,struct.pack('>I',100))
            c.write(0x47ffe-752,struct.pack('>h',0 if case=='locked' else -1))
            c.write(0xdff004,struct.pack('>I',(20 if case=='late' else 8)<<8))
            c.write(BASE+0x33a12,bytes.fromhex('4e75')) # mock native publication ABI
            invoke(c,sy['release_vblank'],flags=flags,supervisor=True)
            assert c.reg(17)&31==flags
            assert all(c.reg(r)==0x34560000+r for r in list(range(1,8))+list(range(9,17)))
            assert c.read(BASE+sy['release_pending'],2)==struct.pack('>H',case not in ('idle','publish'))
            assert c.read(BASE+sy['release_late'],4)==struct.pack('>I',case in ('late','locked'))
            if case=='publish':assert c.read(BASE+sy['release_front'],4)==struct.pack('>I',0x60000)
          c.close()
          rows.append(dict(unit='release_vblank',isa=isa,model=model,cases=160,native_publication='mock RTS'))
    return rows


def rejection_gate(out):
    rejected=[]
    for name,source in (('long_multiply','        mulu.l #10,d0\n'),
                        ('scaled_index','        move.w (a0,d0.w*2),d1\n'),
                        ('read_ccr','        move.w ccr,-(sp)\n')):
        try:assemble(out,'reject-'+name,source,'68000')
        except ValueError:rejected.append(name)
        else:raise AssertionError('base ISA gate accepted '+name)
    for name,source in (('unknown_math','        divs.l d6,d0\n'),
                        ('stack_operand','        move.l (a0,d0.w*2),(sp)\n')):
        try:select(source,'68000')
        except ValueError:rejected.append(name)
        else:raise AssertionError('unreviewed expansion accepted')
    # Positive controls for the arithmetic and X-flag oracles.
    bad=preamble(ROOT,'68000').replace('roxl.w  #1,d0','nop')
    blob,_=assemble(out,'reject-lost-x',bad+'entry:\n        WC_PUSH_CCR\n        move.w (sp)+,ccr\n        rts\n','68000')
    c=CPU(blob,1);invoke(c,0,flags=16);assert c.reg(17)&31!=16;c.close();rejected.append('lost_X')
    bad=preamble(ROOT,'68000')+'entry:\n        WC_MUL_SMALL #9,d0\n        rts\n'
    blob,_=assemble(out,'reject-rate',bad,'68000')
    c=CPU(blob,1);invoke(c,0,{9:123456});assert c.reg(9)!=1234560;c.close();rejected.append('wrong_rate')
    return rejected

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():p.error('fresh tmp directory required')
    out.mkdir(parents=True)
    report={'assembly':assembly_gate(out),'arithmetic':arithmetic_gate(out),'operands_flags':operand_flag_gate(out),'wrappers':wrappers_gate(out),'rejected':rejection_gate(out)}
    report['passed']=True
    report['models']={1:'68000',2:'68020',4:'68040'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in report.items()}))

if __name__=='__main__':main()
