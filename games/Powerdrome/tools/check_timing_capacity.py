#!/usr/bin/env python3
"""Account for sampled world-step delay in an unpaused, single-epoch flight window.

Uses guest VBL, allocator and world-clock observations. Maxima are at world-end
probes, not a bound on unobserved rendering intervals or long-term CPU capacity.
Renderer twins are additional guest work; these are not release throughput figures.
"""
import argparse
import json
from pathlib import Path
import struct
from timing_report import input_state


def u32(data, off):
    return struct.unpack_from('>I', data, off)[0]


def check(root):
    cfg = json.loads((root/'configuration.json').read_text())
    assert int(cfg['ANCHOR'],0) == 0xbc7c
    game = int((root/'game-base.txt').read_text(),0)
    base = int((root/'dump-base.txt').read_text(),0)
    chip = (root/'chip.bin').read_bytes()
    assert struct.unpack_from('>H',chip,game+0xca44)[0] == 0x4ef9
    frame = u32(chip,game+0xca46)-base
    ends=[]
    for code_name,chip_name in (('code.bin','chip.bin'),('final-code.bin','final-chip.bin')):
        data=(root/code_name).read_bytes()
        assert 0 <= frame < len(data)
        def tag(name):
            off=data.find(name,frame,frame+16384)
            assert off>=0, (root,name)
            return off
        pause=input_state(root/code_name)['pause']
        assert not any(pause.values()), 'Unpaused capture required'
        t,w,s=map(tag,(b'PDTIME01',b'PDW20T01',b'PDSESS01'))
        assert struct.unpack_from('>H',data,t+8)[0]==1
        ends.append(dict(wall=u32((root/chip_name).read_bytes(),game+0x48fe)*4,
                         last=u32(data,t+12),debt=u32(data,t+16),
                         clock=u32(data,w+12),epoch=data[s+8:s+40]))
    before,after=ends
    assert before['epoch']==after['epoch'], 'Session/discard ledger changed'
    assert after['wall']-before['wall']==int(cfg['FIELDS'])*4
    rows=[]; current=None
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        v=line.split()
        if not v: continue
        if v[0]=='PDTIME_EVENT':
            current={'field':int(v[1]),'off':int(v[2],16)}
            if current['off']==0xcedc: rows.append(current)
        elif v[0] in ('PDSESSION_EVENT','PDINITIAL_EVENT','PDW20_EVENT'):
            assert current is not None
            assert (int(v[1]),int(v[2],16))==(current['field'],current['off'])
            current[v[0]]=list(map(int,v[3:]))
    assert rows
    delays=[]; debts=[]; batches=[]; components=[]; session=None
    for i,row in enumerate(rows):
        s,v,w=(row[n] for n in ('PDSESSION_EVENT','PDINITIAL_EVENT','PDW20_EVENT'))
        assert (len(s),len(v),len(w))==(23,5,8)
        if session is None:
            session=s[:8]
            assert struct.pack('>8I',*session)==before['epoch']
        assert s[:8]==session and s[8]==s[13]==1, 'Session/ownership changed'
        wall=v[1]*4; last=s[10]; debt=s[11]; left=s[12]; clock=w[0]
        assert clock==s[14]==before['clock']+i*4
        assert 1<=left<=s[9]<=32
        assert wall>=last and debt>=0
        # Current step is observed before its world-end cursor increment.
        assert wall-clock == (wall-last)+debt+(left-1)*4, 'Unaccounted sampled simulation delay'
        delays.append((wall-clock)*5); debts.append(debt*5); batches.append(s[9])
        components.append((row['field'],(wall-last)*5,debt*5,(left-1)*20))
    assert after['clock']-before['clock']==len(rows)*4
    print(f'{root.name}: {len(rows)} paired delay-ledger observations; max world-end probe delay {max(delays)} ms; max retained debt {max(debts)} ms; max allocation {max(batches)} steps')
    field,unsampled,retained,assigned=components[delays.index(max(delays))]
    print(f'  Peak at field {field}: {unsampled} ms unsampled + {retained} ms retained + {assigned} ms in later assigned steps')
    print(f'  Physical window {(after["wall"]-before["wall"])*5} ms; initial/final unsampled elapsed {(before["wall"]-before["last"])*5}/{(after["wall"]-after["last"])*5} ms; endpoint retained debt {before["debt"]*5}/{after["debt"]*5} ms')
    print('  Sampled delay accounting only; not a long-run capacity or maximum render-latency guarantee')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures',type=Path,nargs='+')
    for root in p.parse_args().captures: check(root)
