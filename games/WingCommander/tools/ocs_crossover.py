#!/usr/bin/env python3
"""Experimental C2 boot fixture and stopped-guest installation; never a release."""
import hashlib
import json
import struct
from pathlib import Path
from ocs_c2p import assemble, candidates, source
from ocs_reconstruct import ROOT, require
from variants import ocs

RESERVE = 0x12000
TAIL = 0x14a8
CODE_BYTES = 0x2000

def fixture(out):
    original = (ROOT/ocs.SLAVE).read_bytes()
    require(hashlib.sha256(original).hexdigest() == ocs.SLAVE_SHA, 'changed native slave')
    payload = original[32:-4]+bytes(RESERVE)
    blob = struct.pack('>8I',0x3f3,0,1,0,0,len(payload)//4,0x3e9,len(payload)//4)+payload+struct.pack('>I',0x3f2)
    (out/'WingCommander.Slave').write_bytes(blob)
    return blob


def install(out, layout, arm, command, dump, memory_base=0x200000, memory_length=0x400000):
    """Stopped at pre-submission O:3260a; retire pending native work first."""
    h0,h1 = layout['hunks'][:2]
    base = layout['slave']+TAIL
    fast = base+CODE_BYTES
    memory = dump('install-fast.bin',memory_base,memory_base+memory_length)
    chip = dump('install-chip.bin',0,0x80000)
    def read(p,n=4):
        b = chip[p:p+n] if p<0x80000 else memory[p-memory_base:p-memory_base+n]
        require(len(b)==n,'read outside declared RAM')
        return int.from_bytes(b,'big')
    # The reservation is owned by the loaded slave, not borrowed free memory.
    require(memory_base<=base<fast+64000<=memory_base+memory_length, 'fixture tail outside expansion RAM')
    require(memory_base==0x200000 or not arm.startswith('fast'),'Fast-source arm requires true Fast RAM')
    require(memory[base-memory_base:base-memory_base+RESERVE]==bytes(RESERVE),'fixture tail is not pristine')
    require(all(read(h0+x,1)==0 for x in (0x3291a,0x3291b,0x3291c)), 'pending QBlit at installation')
    surface=read(h0+0x324a8); old=read(surface+4); rows=read(surface+8)
    w,h=read(h0+0x324ac,2),read(h0+0x324ae,2)
    require(w==320 and h in (128,200),'unsupported measured view')
    require(old==read(h0+0x324b0) and old+w*h<=0x80000,'source not native Chip RAM')
    original=(ROOT/ocs.GAME).read_bytes()
    require(hashlib.sha256(original).hexdigest()==ocs.GAME_SHA,'wrong game')
    require(memory[h0+0x3291e-memory_base:h0+0x32924-memory_base]==original[0x3294a:0x32950],'changed displaced submit')
    # Exact native field wait and completion/publication routine are retained.
    # CPU completion runs in the main task; native publication nesting guard is used.
    text=f''' section code,code
entry:
 movem.l d0-d7/a0-a6,-(sp)
 move.l ${h0+0x32916:x},d0
wait_field:
 cmp.l -$800(a4),d0
 beq.s wait_field
 movea.l ${h0+0x324b0:x},a0
 movea.l 64(sp),a2
 movea.l $1c(a2),a1
 moveq #0,d0
 moveq #0,d1
 move.w (a2),d0
 move.w 2(a2),d1
 jsr ocs_c2p_{'long' if arm.endswith('long') else 'word'}(pc)
 tst.l d0
 beq.s completed
 illegal
completed:
 jsr ${h0+0x32e06:x}
 movem.l (sp)+,d0-d7/a0-a6
 rts
'''+source(candidates())
    blob,sy=assemble(out,'adapter',text)
    require(len(blob)<CODE_BYTES,'adapter exceeds reservation')
    def write(name,address,data):
        path=out/(name+'.bin');path.write_bytes(data)
        command(f'monitor ocs-load {address:x} "{path}"')
    write('loaded-adapter',base,blob)
    if arm!='native':
        write('submit-hook',h0+0x3291e,struct.pack('>HI',0x4ef9,base))
    if arm.startswith('fast'):
        # Keep old Chip allocation/registry intact. Only the active view's CPU
        # surface and row table change, and only for this bounded run.
        write('source',fast,chip[old:old+w*h])
        write('surface-pointer',surface+4,struct.pack('>I',fast))
        write('converter-pointer',h0+0x324b0,struct.pack('>I',fast))
        write('rows',rows,b''.join(struct.pack('>I',read(rows+y*4)+fast-old) for y in range(h)))
        aliases=[rows];command_pointers=0
        # O:2be60 copies the primary rows into the compositor's shadow table,
        # substitutes backed rows, and emits 12-byte CPU-copy commands. O:2bf74
        # consumes them; O:2bf40 swaps their source/destination pointers. Rebase
        # both pointer columns, retaining backup allocations and all opcodes.
        a4=layout['a4']
        if read(a4-0x1050):
            shadow=read(a4-0x1048);commands=read(a4-0x1044)
            require(shadow==commands+0xbb8,'unexpected native compositor layout')
            values=[read(shadow+y*4) for y in range(h)]
            require(all(not old<=v<old+w*h or v==old+y*w for y,v in enumerate(values)), 'unexpected shadow row origin')
            write('shadow-rows',shadow,b''.join(struct.pack('>I',v+fast-old if old<=v<old+w*h else v) for v in values))
            aliases.append(shadow)
            edited=bytearray();ended=False
            for n in range(250):
                address=commands+n*12
                if read(address,2)==0xfffa:
                    ended=True;break
                row=bytearray(memory[address-memory_base:address-memory_base+12])
                require(len(row)==12,'command stream outside pool')
                for column in (4,8):
                    value=read(address+column)
                    if old<=value<old+w*h:
                        struct.pack_into('>I',row,column,value+fast-old);command_pointers+=1
                edited+=row
            require(ended,'unterminated compositor stream')
            if edited:write('compositor-commands',commands,edited)
    result=dict(arm=arm,width=w,height=h,source=fast if arm.startswith('fast') else old,
                original_source=old,code=base,tail_bytes=RESERVE,
                sha256=hashlib.sha256(blob).hexdigest(),symbols=sy,
                production=False,source_allocation_retained=True,
                row_aliases=aliases if arm.startswith('fast') else [],
                compositor_pointers=command_pointers if arm.startswith('fast') else 0)
    (out/'installation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
