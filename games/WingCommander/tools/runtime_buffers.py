"""Move explicit zero workspaces to the single hunk's loader-allocated tail.

The AmigaDOS hunk allocation size includes the tail; HUNK_CODE stores only
initialized bytes. An entry wrapper explicitly clears the tail before the
original loader, independent of the loader's clearing policy. No extra hunk,
absolute relocation or game-heap loan.
"""
import re
import struct

# Preserve each block's internal layout and aliases. Small control words and
# nonzero initialization stay in the initialized code/data portion.
BLOCKS = (
    ('timing_scene_snapshot_data:', 'timing_scene_saved_end:'),
    ('projectile_types:', 'projectile_cooldown_valid: dcb.b 64,0'),
)
SINGLES = ('timing_input_ring', 'ocs_input_ring', 'ocs_exhaust_mounts',
           'field_shot_fractions', 'field_shot_contacts', 'modal_bar_records',
           'funeral_before', 'funeral_after', 'flight_history_storage',
           'ocs_changed_history')


def source(text, entry):
    blocks=[]
    for first,last in BLOCKS:
        if first not in text:continue
        start=text.index(first);end=text.index(last,start)+len(last)
        blocks.append(text[start:end]);text=text[:start]+text[end:]
    for label in SINGLES:
        pattern=rf'^{label}:\s*(?:ds\.[bwl]\s+[^\n]+|dcb\.[bwl]\s+[^\n]+)$'
        match=re.search(pattern,text,re.M)
        if match:
            blocks.append(match[0]);text=text[:match.start()]+text[match.end():]
    names=set(re.findall(r'^(\w+):', '\n'.join(blocks), re.M))
    count=0;lines=[]
    for line in text.splitlines():
        code=line.split(';',1)[0]
        match=re.search(r'\b(\w+(?:\+\d+)?)\(pc\)',code)
        if not match or match[1].split('+')[0] not in names:
            lines.append(line);continue
        count+=1;target=match[1];anchor=f'.workspace_address_{count}'
        lea=re.match(r'\s*lea\s+[^,]+,(a[0-6])\s*$',code)
        if lea:
            reg=lea[1]
            lines += [f' lea {anchor}(pc),{reg}',anchor+':',f' adda.l #{target}-{anchor},{reg}']
        else:
            # Only ordinary non-stack data operations occur at these sites.
            if not re.match(r'\s*(tst\.[bw]|move\.[bwl]|cmp\.[bw])\s',code) or 'sp' in code:
                raise ValueError('unaudited workspace operand: '+line)
            reg=next(f'a{i}' for i in range(6,-1,-1) if not re.search(rf'\ba{i}\b',code))
            lines += [f' movem.l {reg},-(sp)',f' lea {anchor}(pc),{reg}',anchor+':',
                      f' adda.l #{target}-{anchor},{reg}',line.replace(match[0],f'({reg})'),
                      f' movem.l (sp)+,{reg}']
    text='\n'.join(lines)
    marker='release_setcpu:' if 'release_setcpu:' in text else 'install:'
    init=f"""runtime_workspace_init:
 movem.l d0/a0,-(sp)
 lea runtime_workspace_init(pc),a0
 adda.l #runtime_workspace-runtime_workspace_init,a0
 move.l #(runtime_workspace_end-runtime_workspace)/4,d0
.runtime_clear:
 clr.l (a0)+
 subq.l #1,d0
 bne.s .runtime_clear
 movem.l (sp)+,d0/a0
 bra.w slave+${entry:x}
"""
    assert marker in text
    text=text.replace(marker,init+marker,1)
    # Backend range certification must cover the allocation, not just code.
    text=text.replace('#payload_end-install', '#runtime_workspace_end-install')
    return text+'\n cnop 0,4\nruntime_workspace:\n'+'\n cnop 0,4\n'.join(blocks)+'\n cnop 0,4\nruntime_workspace_end:\n'



def container(payload, initialized):
    assert len(payload)%4==initialized%4==0
    assert 0<initialized<=len(payload)
    assert not any(payload[initialized:]), 'nonzero data in runtime workspace'
    return (struct.pack('>8I',0x3f3,0,1,0,0,len(payload)//4,0x3e9,initialized//4)
            +payload[:initialized]+struct.pack('>I',0x3f2))


def load(blob):
    """Model single-hunk loading, including its zeroed allocation tail."""
    h=struct.unpack_from('>8I',blob)
    assert h[:5]==(0x3f3,0,1,0,0) and h[6]==0x3e9
    size,stored=h[5]*4,h[7]*4
    assert size>=stored and len(blob)==stored+36
    assert blob[-4:]==struct.pack('>I',0x3f2)
    return blob[32:-4]+bytes(size-stored)
