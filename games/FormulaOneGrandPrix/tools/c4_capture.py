"""C4 input acceptance probes using real harness input, never memory writes."""
import hashlib
import json
import re
import struct


def exercise(args, command, out, base, bases, symbols, meta):
    assert args.custom4 == 3 and args.route == 'quickrace'
    h0, h1, h2, _ = bases
    observations = []
    result = dict(status='INCOMPLETE', observations=observations)
    meta['input'] = result
    def read(name, address, size):
        path = out/(name+'.bin')
        command('gdb', f'dump binary memory {path} {address:#x} {address+size:#x}')
        return path.read_bytes()
    def stop(address, condition=None):
        command('gdb','delete breakpoints')
        command('gdb',f'break *{address:#x}')
        if condition:
            command('gdb',f'condition $bpnum {condition}')
        command('gdb','continue')
        pc = re.search(r'\$\d+\s*=\s*(0x[0-9a-fA-F]+)',command('gdb','p/x $pc'))
        assert pc and int(pc[1],16)==address, pc
        command('gdb','delete breakpoints')
    def snap(name):
        state = read(name+'-slave',base,symbols['c2_beam_max']+2)
        native = read(name+'-h0',h0,0x3ca00)
        view = read(name+'-view',h1+0x234,14)
        keys = read(name+'-keys',h2+0x52a,128)
        player = struct.unpack_from('>I',native,0x3a720)[0]
        controls = read(name+'-control',player+0x7f,1) if player else b''
        item = dict(name=name, ticks=struct.unpack_from('>I',state,symbols['c2_clock']+24)[0],
                    batch=struct.unpack_from('>H',state,symbols['c2_clock']+10)[0],
                    draw_mode=struct.unpack_from('>H',state,symbols['c2_draw_mode'])[0],
                    serial=struct.unpack_from('>I',state,symbols['c2_serial'])[0],
                    masks=native[0x18:0x1e].hex(), latch=native[0x3a915],
                    view=view.hex(), event=view[10], key=keys[0x4f],
                    control=controls.hex(), player=player,
                    buffer=dict(deferred=struct.unpack_from('>I',state,symbols['c4_deferred'])[0],
                                applied=struct.unpack_from('>I',state,symbols['c4_applied'])[0],
                                live=struct.unpack_from('>H',state,symbols['c4_live'])[0],
                                state=state[symbols['c4_keys']+0x4f]),
                    files={suffix:hashlib.sha256(data).hexdigest() for suffix,data in
                           (('slave',state),('h0',native),('view',view),('keys',keys))})
        if controls:
            item['files']['control']=hashlib.sha256(controls).hexdigest()
        observations.append(item)
        (out/'input.json').write_text(json.dumps(result,indent=2)+'\n')
        return item
    # Anchor to completed world ticks, not a cross-build field count.
    stop(h0+0x3c94a, f'*(unsigned int*){base+symbols["c2_clock"]+24:#x} >= 30')
    snap('anchor')
    command('gdb','monitor key 4f 1')
    stop(h2+0x4d4)
    assert snap('held-irq')['key'] == 0xb3
    held=[]
    for n in range(5):
        stop(h0+0x3c99a)
        held.append(snap(f'held-{n}'))
    sampled = [not bool(int(x['masks'],16)&0x2000) for x in held]
    edges = [v and (n==0 or not sampled[n-1]) for n,v in enumerate(sampled)]
    assert sum(edges)==1 and [bool(x['event']&0x20) for x in held]==edges, held
    assert any(x['draw_mode']==2 for x in held), 'no catch-up tick covered'
    command('gdb','monitor key 4f 0')
    stop(h2+0x4d4)
    assert snap('release-irq')['key']==0
    stop(h0+0x3c950)
    stop(h0+0x3c99a)
    assert not snap('released')['latch']&0x20
    # The controller is sampled afresh in the native per-tick call.
    command('gdb','monitor input JOY2_RIGHT 1')
    command('gdb','monitor fields 1')
    stop(h0+0x3c956)
    right=snap('stick-right')
    assert int(right['control'],16)&8, right
    command('gdb','monitor input JOY2_RIGHT 0')
    command('gdb','monitor fields 1')
    stop(h0+0x3c956)
    neutral=snap('stick-neutral')
    assert not int(neutral['control'],16)&8, neutral
    # Stop before the diagnostic 20-field delay, after a batch finishes.
    stop(base+symbols['c2_acquire'])
    before=snap('pulse-before')
    command('gdb','monitor key 4f 1')
    stop(h2+0x4d4)
    down=snap('pulse-down')
    assert down['key']==0xb3
    command('gdb','monitor key 4f 0')
    stop(h2+0x4d4)
    up=snap('pulse-up')
    # The buffer holds the release back: the table still shows the press.
    assert up['key']==0xb3 and up['buffer']['deferred']==down['buffer']['deferred']+1, up
    # No simulation tick ran between the actual keyboard IRQ stores.
    assert before['ticks']==down['ticks']==up['ticks'], (before,down,up)
    stop(h0+0x3c950)
    scanned=snap('pulse-scan')
    stop(h0+0x3c99a)
    consumed=snap('pulse-consumer')
    # The next scan shows the held-back release; the press must act only once.
    stop(h0+0x3c950)
    released=snap('pulse-release')
    stop(h0+0x3c99a)
    after=snap('pulse-after')
    once = (released['key']==0 and int(released['masks'],16)&0x2000
            and released['buffer']['applied']==scanned['buffer']['applied']+1
            and released['ticks']==scanned['ticks']+1
            and not after['event']&0x20 and not after['latch']&0x20)
    result.update(held_view='PASS', joystick='PASS', short_pulse=(
        'PASS' if not int(scanned['masks'],16)&0x2000 and consumed['event']&0x20 and once
        else 'FAIL'))
    result['status']='PASS' if result['short_pulse']=='PASS' else 'FAIL'
    (out/'input.json').write_text(json.dumps(result,indent=2)+'\n')
