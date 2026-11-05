#!/usr/bin/env python3
"""A3 call-boundary state capture. Server: statediff live|replay DIR [FRAMES].
Snapshot whole hunks, including interleaved code/data and h3 screens, so no guessed
code/data split silently excludes a write. Reports separate proven screen ranges.
Deltas include interrupt activity and omit write/restore pairs; they are evidence,
not an automatic ownership or completeness proof. Raw snapshots stay in tmp/.
"""
import collections
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
from slave_inputs import ROOT, verify
from state_classes import ASYNC, contains, draw_class, CALLS
from race_profile import game_hunks, image, locate

SIZES = (0x44a54, 0x2a940, 0x41c70, 0x14f84)
LOOPS = {'live': (0x3c8f6, 0x3ca56), 'replay': (0x3cc40, 0x3cd0c)}


def scratch(path):
    p = Path(path).resolve()
    if not p.is_relative_to(ROOT/'tmp'):
        raise ValueError('state evidence must stay in tmp/')
    return p


def digest(data):
    return hashlib.sha256(data).hexdigest()


def capture(server, g, rest):
    mode, dest, *tail = rest.split()
    frames = int(tail[0]) if tail else 50
    if mode not in LOOPS or len(tail)>1 or frames < 1:
        raise ValueError('statediff live|replay DIR [FRAMES]')
    verify()
    out = scratch(dest)
    out.mkdir(parents=True, exist_ok=False)
    g.stop()
    def cmd(s):
        with (out/'commands.log').open('a') as log:
            log.write('> '+s+'\n')
        answer = g.cmd(s, timeout=120)
        with (out/'commands.log').open('a') as log:
            log.write(answer+'\n')
        if any(x in answer for x in ('Cannot ', 'Error', 'not supported', 'Command aborted', 'Protocol error', 'Invalid hex digit')):
            raise RuntimeError(answer)
        return answer
    cmd(f'dump binary memory {out}/fast.bin 0x200000 0xa00000')
    cmd(f'dump binary memory {out}/chip.bin 0 0x200000')
    mem = image((out/'chip.bin').read_bytes(), (out/'fast.bin').read_bytes(), b'')
    found = locate(mem, game_hunks())
    h0, h2 = found[0][0], found[2][0]
    nxt = lambda h: struct.unpack_from('>I',mem,h-4)[0]*4+4
    bases = [h0, nxt(h0), h2, nxt(h2)]
    # Restrict to known direct absolute JSRs; validate each against the current game.
    start, end = LOOPS[mode]
    # Full instruction walk prevents accidental opcode matches inside operands.
    from amigaxdev.disasm import records
    insns = list(records(str(out/'fast.bin'),0x200000,h0,start,end+4))
    sites = {off: struct.unpack_from('>I',mem,h0+off+2)[0]
             for off,raw,text in insns if text.startswith('jsr ')}
    if any(mem[h0+off:h0+off+2] != b'\x4e\xb9' for off in sites):
        raise ValueError('unsupported call form')
    # h0+124A is the first bitmap; h2+231DA is its stride. Keep raw screen bytes too.
    screen = struct.unpack_from('>I', mem,h0+0x124a)[0]
    stride = struct.unpack_from('>I',mem,h2+0x231da)[0]
    screens = [(screen,screen+32000),(screen+stride,screen+stride+32000)]
    if stride < 32000 or not all(bases[3] <= a < b <= bases[3]+SIZES[3] for a,b in screens):
        raise ValueError(f'unexpected bitmap layout: {screens}, stride={stride}')
    slave = Path(os.environ['SLAVE'])
    meta = dict(status='CAPTURING',mode=mode,frames=frames,hunk_bases=bases,
                hunk_sizes=SIZES,screens=screens,calls={str(k):v for k,v in sites.items()},
                slave_sha256=digest(slave.read_bytes()),
                game_inputs=json.loads((ROOT/'manifest/game-inputs.json').read_text()),
                setup=os.environ.get('AMIGA_SETUP'),whd_args=os.environ.get('WHD_ARGS',''),
                emulator_sha256=digest(Path(os.environ['FSUAE']).read_bytes()))
    (out/'meta.json').write_text(json.dumps(meta,indent=2)+'\n')
    serial=0
    def snap(frame,site,edge):
        nonlocal serial
        pieces=[]
        for h,(base,size) in enumerate(zip(bases,SIZES)):
            raw=out/'scratch.bin'
            for attempt in range(3):
                raw.unlink(missing_ok=True)
                try:
                    cmd(f'dump binary memory {raw} {base:#x} {base+size:#x}')
                    part=raw.read_bytes()
                    break
                except RuntimeError as error:
                    # A malformed read reply does not advance the halted CPU. Retry
                    # that read only, never continue/step or an input operation.
                    if 'Invalid hex digit' not in str(error) or attempt==2:
                        raise
            else:
                raise ValueError('dump failed')
            if len(part)!=size:
                raise ValueError('short dump')
            pieces.append(part)
        data=b''.join(pieces)
        name=f'{serial:05d}.bin.gz'
        with gzip.open(out/name,'wb',compresslevel=1) as f:
            f.write(data)
        item=dict(serial=serial,frame=frame,site=site,edge=edge,file=name,sha256=digest(data))
        with (out/'events.jsonl').open('a') as f:
            f.write(json.dumps(item)+'\n')
        serial+=1
    def pc():
        answer=cmd('p/x $pc')
        return int(re.search(r'= (0x[0-9a-f]+)',answer)[1],16)-h0
    cmd('delete')
    try:
        cmd(f'break *{h0+start:#x}')
        cmd('continue')
        if pc()!=start:
            raise ValueError('did not reach loop head')
        cmd('delete')
        for frame in range(frames):
            steps=0
            while True:
                off=pc()
                if off==end:
                    break
                if not start <= off < end:
                    raise ValueError(f'left {mode} loop at {off:x}')
                if off in sites:
                    snap(frame,off,'before')
                    cmd(f'break *{h0+off+6:#x}')
                    cmd('continue')
                    cmd('delete')
                    if pc()!=off+6:
                        raise ValueError(f'call {off:x} did not return')
                    snap(frame,off,'after')
                else:
                    cmd('stepi')
                steps+=1
                if steps>200:
                    raise ValueError('loop did not complete within 200 boundary steps')
            print(f'A3 {mode} frame {frame+1}/{frames}',flush=True)
            cmd('stepi')
        meta['status']='CAPTURED'
        meta['snapshots']=serial
        (out/'meta.json').write_text(json.dumps(meta,indent=2)+'\n')
        (out/'scratch.bin').unlink(missing_ok=True)
    except Exception as error:
        meta.update(status='FAILED',error=str(error),snapshots=serial)
        (out/'meta.json').write_text(json.dumps(meta,indent=2)+'\n')
        raise
    finally:
        cmd('delete')
    return f'{frames} complete {mode} frames, {serial} snapshots in {out}'


def spans(offsets):
    result=[]
    for off in sorted(offsets):
        if result and result[-1][1]==off:
            result[-1][1]=off+1
        else:
            result.append([off,off+1])
    return result


def changed_offsets(a,b):
    """Skip identical blocks (most captured bytes are code or unchanged tables)."""
    if len(a)!=len(b):
        raise ValueError('different snapshot lengths')
    for start in range(0,len(a),4096):
        left,right=a[start:start+4096],b[start:start+4096]
        if left!=right:
            yield from (start+n for n,(x,y) in enumerate(zip(left,right)) if x!=y)


def report(path):
    out=scratch(path)
    meta=json.loads((out/'meta.json').read_text())
    verify()
    if meta['status']!='CAPTURED':
        raise ValueError('capture is incomplete')
    if meta['game_inputs']!=json.loads((ROOT/'manifest/game-inputs.json').read_text()):
        raise ValueError('game input metadata mismatch')
    if meta['mode'] not in LOOPS or meta['hunk_sizes']!=list(SIZES):
        raise ValueError('invalid mode or hunk sizes')
    mem=image((out/'chip.bin').read_bytes(),(out/'fast.bin').read_bytes(),b'')
    found=locate(mem,game_hunks())
    h0,h2=found[0][0],found[2][0]
    nxt=lambda h:struct.unpack_from('>I',mem,h-4)[0]*4+4
    if meta['hunk_bases']!=[h0,nxt(h0),h2,nxt(h2)]:
        raise ValueError('hunk layout does not match captured RAM')
    screen=struct.unpack_from('>I',mem,h0+0x124a)[0]
    stride=struct.unpack_from('>I',mem,h2+0x231da)[0]
    if meta['screens']!=[[screen,screen+32000],[screen+stride,screen+stride+32000]]:
        raise ValueError('screen exclusions do not match captured RAM')
    for site,target in meta['calls'].items():
        off=int(site)
        start,end=LOOPS[meta['mode']]
        if not start<=off<end or mem[h0+off:h0+off+2]!=b'\x4e\xb9' or struct.unpack_from('>I',mem,h0+off+2)[0]!=target:
            raise ValueError('call metadata does not match captured RAM')
    events=[json.loads(x) for x in (out/'events.jsonl').read_text().splitlines()]
    if len(events)%2 or len(events)!=meta['snapshots']:
        raise ValueError('incomplete event pairs')
    if any(e['serial']!=n or str(e['site']) not in meta['calls'] or not 0<=e['frame']<meta['frames'] for n,e in enumerate(events)):
        raise ValueError('invalid event sequence')
    expected_draw=0x3c9ba if meta['mode']=='live' else 0x3cce8
    expected_pacer=0x3c9d2 if meta['mode']=='live' else 0x3cd06
    for site in (expected_draw,expected_pacer):
        if [e['frame'] for e in events if e['site']==site and e['edge']=='after']!=list(range(meta['frames'])):
            raise ValueError('missing complete draw/pacer frames')
    result={site:dict(calls=0,changed=[set() for _ in SIZES],screen_bytes=set()) for site in meta['calls']}
    for before,after in zip(events[::2],events[1::2]):
        if (before['site'],before['frame'],before['edge'],after['edge']) != (after['site'],after['frame'],'before','after'):
            raise ValueError('unpaired snapshots')
        a,b=(gzip.decompress((out/e['file']).read_bytes()) for e in (before,after))
        if len(a)!=sum(SIZES) or len(b)!=sum(SIZES):
            raise ValueError('short snapshot')
        if digest(a)!=before['sha256'] or digest(b)!=after['sha256']:
            raise ValueError('snapshot hash mismatch')
        item=result.setdefault(str(before['site']),dict(calls=0,changed=[set() for _ in SIZES],screen_bytes=set()))
        item['calls']+=1
        pos=0
        for h,(base,size) in enumerate(zip(meta['hunk_bases'],SIZES)):
            for off in changed_offsets(a[pos:pos+size],b[pos:pos+size]):
                if any(lo<=base+off<hi for lo,hi in meta['screens']):
                    item['screen_bytes'].add(off)
                else:
                    item['changed'][h].add(off)
            pos+=size
    unknown=[]
    for site,item in result.items():
        target=meta['calls'][site]
        key=next(((h,target-base) for h,(base,size) in enumerate(zip(meta['hunk_bases'],SIZES)) if base<=target<base+size),None)
        item['class']=CALLS.get(key,'UNCLASSIFIED')
        if item['class']=='UNCLASSIFIED':unknown.append([site,'target',target])
        classes=collections.Counter()
        for h,offsets in enumerate(item['changed']):
            for off in offsets:
                cls=draw_class(h,off) if key==(2,0x280f6) else ('asynchronous' if contains(ASYNC,h,off) else item['class'])
                classes[cls]+=1
                if cls=='UNCLASSIFIED':unknown.append([site,h,off])
        item['classes']=dict(classes)
        item['changed_bytes']=[len(x) for x in item['changed']]
        item['changed']=[spans(x) for x in item['changed']]
        item['screen_bytes']=len(item['screen_bytes'])
    answer=dict(status='CLASSIFIED' if not unknown else 'UNCLASSIFIED',frames=meta['frames'],calls=result,unclassified=unknown,
                caveat='Net deltas include interrupts; write/restore and same-value stores require trace/static audit.')
    (out/'diff.json').write_text(json.dumps(answer,indent=2)+'\n')
    print('unclassified:',len(unknown))
    print(json.dumps({hex(int(k)):dict(calls=v['calls'],changed=v['changed_bytes'],screen=v['screen_bytes']) for k,v in result.items()},indent=2))

    return answer


if __name__=='__main__':
    if report(sys.argv[1])['status']!='CLASSIFIED':
        raise SystemExit(1)
