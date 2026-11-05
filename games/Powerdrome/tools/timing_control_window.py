"""Exact completed-control count for unpaused, single-epoch WORLD20 windows."""
import re
import struct
from check_timing_capacity import check as check_capacity
from timing_report import input_state


def check_control_window(root, ticks, epoch):
    # Independently account for physical elapsed time, retained/assigned work,
    # every completed world step, and an unchanged session/discard ledger.
    check_capacity(root)
    first=input_state(root/'code.bin')
    last=input_state(root/'final-code.bin')
    assert not first['control_active'] and not last['control_active'], 'Incomplete boundary control'
    game=int((root/'game-base.txt').read_text(),0)
    base=int((root/'dump-base.txt').read_text(),0)
    chip=(root/'chip.bin').read_bytes()
    frame=struct.unpack_from('>I',chip,game+0xca46)[0]-base
    data=(root/'final-code.bin').read_bytes()
    world=data.find(b'PDW20T01',frame,frame+16384)
    assert world>=0
    end=struct.unpack_from('>I',data,world+12)[0]
    # The cursor points at the next movement. A control deadline is eligible
    # only at/before the final completed movement timestamp (cursor minus 4).
    expected=max(0,(end-4-first['clock'])//18+1)
    # A capture may stop after a control completes but before its containing
    # movement reaches cedc. Prove that boundary from independent ownership,
    # started-step counters and the post-control ccee observation; never infer
    # an allowance from the number of rows being checked.
    if last['clock']==first['clock']+18*(expected+1):
        initial=(root/'code.bin').read_bytes()
        owner=data.find(b'PDWORLD1',frame,frame+16384)
        assert owner>=0 and struct.unpack_from('>H',data,owner+8)[0]==1
        assert struct.unpack_from('>H',data,world+10)[0]==1
        start=struct.unpack_from('>I',initial,world+12)[0]
        assert (end-start)%4==0
        begun=struct.unpack_from('>I',data,world+16)[0]-struct.unpack_from('>I',initial,world+16)[0]
        assert begun==(end-start)//4+1, 'Extra control without one unfinished world step'
        slow=struct.unpack_from('>I',data,world+20)[0]-struct.unpack_from('>I',initial,world+20)[0]
        assert slow==expected+1, 'Unaccounted started controls'
        deadline=first['clock']+18*expected
        assert end-4<deadline<=end, 'Extra control is not due in the unfinished movement'
        log=(root/'swaps-gdb.txt').read_text()
        pending=[list(map(int,v.split())) for v in re.findall(
            r'^PDW20_EVENT -?\d+ 0xccee (.+)$',log,re.M)
            if int(v.split()[0])==end]
        assert len(pending)==1, 'Missing post-control observation in unfinished movement'
        assert pending[0][:5]==[end,struct.unpack_from('>I',data,world+16)[0],
                                struct.unpack_from('>I',data,world+20)[0],1,last['clock']]
        expected+=1
        print(f'  One completed control belongs to the unfinished world step at {end}; counted from independent boundary evidence')
    assert len(ticks)==expected, 'Control count differs from completed world-time coverage'
    assert ticks==[first['clock']-epoch+18*i for i in range(expected)], 'Missing or repeated control deadline'
    assert last['clock']==first['clock']+18*expected, 'Unobserved final control-clock mutation'
    return ticks[0],ticks[-1]
