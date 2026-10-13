#!/usr/bin/env python3
"""Decode the live world-update control-flow inventory; derived listings stay in tmp/."""
import argparse, hashlib, json, struct
import capstone as cs
from capstone import m68k as m
from cd32_runtime import ROOT, BASE, SIZES, locate


def inventory(memory, layout, roots):
    decoder=cs.Cs(cs.CS_ARCH_M68K,cs.CS_MODE_BIG_ENDIAN|cs.CS_MODE_M68K_020)
    decoder.detail=True
    h=layout['hunks']
    def label(a):
        for n in (0,3):
            if h[n]<=a<h[n]+SIZES[n]:return f'{"E" if n==0 else "H3"}:{a-h[n]:05x}'
        if layout['slave']<=a<layout['slave']+0x1e0c:return f'S:{a-layout["slave"]:05x}'
        return f'external:{a:08x}'
    def code(a):return any(h[n]<=a<h[n]+SIZES[n] for n in (0,3))
    def ins(a):return next(decoder.disasm(memory[a-BASE:a-BASE+16],a,1),None)
    def target(i):
        o=i.operands[-1]
        if o.type==m.M68K_OP_BR_DISP:return i.address+2+o.br_disp.disp
        if o.address_mode in (m.M68K_AM_ABSOLUTE_DATA_LONG,m.M68K_AM_ABSOLUTE_DATA_SHORT):return o.imm
        if o.address_mode==m.M68K_AM_PCI_DISP:return i.address+2+o.mem.disp
        return None
    # These are leaf subsystem boundaries, not unexamined simulation dispatches.
    # Their computed jumps select copy/fill lengths or OS/runtime callbacks.
    boundaries = {
        **dict.fromkeys((0x28a40,0x28a50), 'resource byte-copy run length'),
        **dict.fromkeys((0x2cfd6,0x2f144,0x2f17a,0x2f1ee,0x302a0,0x302ec,
                        0x30e58,0x3195e,0x3197c,0x31d22,0x31d9e),
                       'image copy/fill/bitstream kernel'),
        **dict.fromkeys((0x2f4c2,0x2f4f8,0x2f63e,0x2f6d4),
                       'formatted text output callback'),
        **dict.fromkeys((0x3489c,0x34928), 'C byte/long memory-copy kernel'),
        **dict.fromkeys((0x34f08,0x35c6c,0x35c82,0x35cd8),
                       'C runtime exit/stdio callback'),
    }
    todo=[h[0]+x for x in roots];seen={};edges=[];unresolved=[];tables=[];external=[];leaves=[]
    while todo:
        a=todo.pop()
        if a in seen:continue
        if not code(a):external.append(label(a));continue
        i=ins(a)
        if not i or i.mnemonic.startswith(('dc.','invalid')):raise ValueError('invalid decode '+label(a))
        seen[a]=i;name=i.mnemonic.split('.')[0];nxt=a+i.size
        if name in ('rts','rte','rtr','stop','illegal'):continue
        if name in ('jmp','jsr','bsr','bra') or name.startswith(('db','fb')) or (name.startswith('b') and name not in ('bchg','bclr','bset','btst','bfchg','bfclr','bfexts','bfextu','bfffo','bfins','bfset','bftst')):
            dest=target(i)
            if dest is not None:
                edges.append(dict(at=label(a),kind=name,target=label(dest)));todo.append(dest)
            elif a==h[0]+0x13d60:
                table=h[1]+0x372
                entries=list(struct.unpack_from('>47I',memory,table-BASE))
                if not all(code(x) for x in entries):raise ValueError('non-code ship-action dispatch')
                tables.append(dict(at=label(a),table='D:00372',entries=[label(x) for x in entries]))
                todo.extend(entries)
            elif a-h[0] in (0x277b4,0x309a4,0x30b02):
                entries=[h[0]+x for x in ((0x27856,0x278fc) if a-h[0]==0x277b4 else (0x34620,0x3460a))]
                edges.extend(dict(at=label(a),kind='selected-resource-helper',target=label(x)) for x in entries)
                todo.extend(entries)
            elif a==h[0]+0x2fdde:
                table=h[0]+0x2fde2
                # Byte index doubled with ADD.B: 128 word entries, not 256.
                entries=[table+struct.unpack_from('>h',memory,table-BASE+2*j)[0] for j in range(128)]
                tables.append(dict(at=label(a),table=label(table),entries=[label(x) for x in entries]))
                todo.extend(entries)
            elif a-h[0] in boundaries:
                leaves.append(dict(at=label(a),reason=boundaries[a-h[0]]))
            elif name=='jsr' and i.operands[0].address_mode==m.M68K_AM_REGI_ADDR_DISP and i.operands[0].mem.base_reg==m.M68K_REG_A6 and i.operands[0].mem.disp<0:
                leaves.append(dict(at=label(a),reason='OS library negative vector'))
            elif name=='jmp' and memory[a-BASE:a-BASE+2]==bytes.fromhex('4efb'):
                # Aztec C bounded word-offset switch: cmp count; bcc default;
                # add.w d0,d0; move.w table(pc,d0.w),d0; jmp 0(pc,d0.w).
                cmp_at=next((a-n for n in (12,14) if memory[a-BASE-n:a-BASE-n+2]==bytes.fromhex('0c40')),None)
                raw=memory[a-BASE-6:a-BASE]
                if cmp_at is not None and memory[cmp_at-BASE+4]==0x64 and raw[:4]==bytes.fromhex('d040303b'):
                    count=struct.unpack_from('>H',memory,cmp_at-BASE+2)[0]
                    table=a-2+struct.unpack('b',raw[-1:])[0]
                    base=a+2+struct.unpack('b',memory[a-BASE+3:a-BASE+4])[0]
                    entries=[base+struct.unpack_from('>h',memory,table-BASE+2*j)[0] for j in range(count)]
                    if not all(code(x) for x in entries):raise ValueError('non-code switch destination at '+label(a))
                    tables.append(dict(at=label(a),table=label(table),entries=[label(x) for x in entries]))
                    todo.extend(entries)
                else:unresolved.append(dict(at=label(a),instruction=i.mnemonic+' '+i.op_str))
            else:unresolved.append(dict(at=label(a),instruction=i.mnemonic+' '+i.op_str))
            if name in ('jmp','bra'):continue
        todo.append(nxt)
    return dict(roots=[label(h[0]+x) for x in roots],instructions=len(seen),edges=sorted(edges,key=lambda x:x['at']),tables=sorted(tables,key=lambda x:x['at']),unresolved=sorted(unresolved,key=lambda x:x['at']),boundaries=sorted(leaves,key=lambda x:x['at']),external=sorted(set(external))),seen


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');p.add_argument('--output',required=True);a=p.parse_args()
    run=ROOT/a.run;out=(ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('fresh tmp output required')
    memory=(run/'start-fast.bin').read_bytes();layout=locate(memory)
    report,seen=inventory(memory,layout,[0x2a8])
    if report['unresolved']:raise ValueError('unclassified indirect transfer: '+str(report['unresolved']))
    if set(report['external'])!={'S:016fc','S:0176a'}:raise ValueError('unexpected external code edge')
    report['decoder_version']=cs.__version__
    report['dump_sha256']=hashlib.sha256(memory).hexdigest();out.mkdir(parents=True)
    (out/'inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    h=layout['hunks']
    (out/'reachable.dis').write_text('\n'.join(f'{"E" if h[0]<=at<h[0]+SIZES[0] else "H3"}:{at-(h[0] if h[0]<=at<h[0]+SIZES[0] else h[3]):05x} {i.mnemonic} {i.op_str}' for at,i in sorted(seen.items()))+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('edges','tables')},indent=2))
    print('tables',len(report['tables']),'edges',len(report['edges']))

if __name__=='__main__':main()
