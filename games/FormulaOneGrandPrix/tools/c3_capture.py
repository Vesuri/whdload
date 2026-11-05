"""C3 native UI routes, used by c2_capture --modal. Evidence remains in tmp/."""
import hashlib
import json
import struct
import re
from PIL import Image
from f1gp import showing


def exercise(args, command, out, base, bases, symbols, meta):
    observations = []
    meta['modal'] = dict(scenario=args.modal, observations=observations, status='INCOMPLETE')
    def fields(n):
        command('gdb', f'monitor fields {n}')
    def snapshot(name, picture=True):
        path = out / (name + '.bin')
        end = symbols['c2_beam_max']+2
        command('gdb', f'dump binary memory {path} {base:#x} {base+end:#x}')
        data = path.read_bytes()
        words = ('c2_mode','c2_in_tick','c2_draw_mode','c2_scene_ready','c3_suspended','c2_hud_count','c3_inactive','c2_hud_replaying')
        longs = ('c2_serial','c3_epochs','c3_exits','c3_pauses','c3_reconstructions',
                 'c3_rebased','c3_excluded','c2_hud_queued','c2_hud_painted','c2_hud_overflows')
        item = dict(name=name, sha256=hashlib.sha256(data).hexdigest())
        item.update({n: struct.unpack_from('>H', data, symbols[n])[0] for n in words})
        item.update({n: struct.unpack_from('>I', data, symbols[n])[0] for n in longs})
        vals = struct.unpack_from('>I4H4I', data, symbols['c2_clock'])
        item['clock'] = dict(zip(('last','credit','rate','phase','batch','observed','consumed','dropped','ticks'),vals))
        c = item['clock']
        assert c['observed'] == (c['consumed']+c['credit']+c['dropped']+item['c3_rebased'])&0xffffffff, item
        assert item['c2_hud_overflows'] == 0, item
        if not item['c2_in_tick'] and not item['c2_hud_replaying']:
            assert item['c2_hud_queued'] == item['c2_hud_painted']+item['c2_hud_count'], item
        cars = out/(name+'-cars.bin')
        command('gdb', f'dump binary memory {cars} {bases[1]+0x368:#x} {bases[1]+0x1956:#x}')
        item['cars_sha256'] = hashlib.sha256(cars.read_bytes()).hexdigest()
        native = out/(name+'-session.bin')
        command('gdb', f'dump binary memory {native} {bases[0]+0x3a714:#x} {bases[0]+0x3a7d4:#x}')
        session = native.read_bytes()
        item['session_sha256'] = hashlib.sha256(session).hexdigest()
        item['start_phase'] = session[0x3a750-0x3a714]
        item['pit_animation'] = struct.unpack_from('>4H',session,0x3a746-0x3a714)
        if picture:
            command('shot', str(out/(name+'.png')))
        observations.append(item)
        (out/'modal.json').write_text(json.dumps(meta['modal'], indent=2)+'\n')
        return item
    def pause(name):
        command('tap','40')
        fields(50)
        a = snapshot(name+'-start')
        assert a['c3_suspended'] == 1 and a['c2_in_tick'] == 0, a
        fields(250)
        b = snapshot(name+'-held')
        assert b['clock'] == a['clock'] and b['cars_sha256'] == a['cars_sha256'] and b['session_sha256'] == a['session_sha256'], (a,b)
        assert b['c2_serial']-a['c2_serial'] >= 250
        return b
    def resume(name, held):
        # Stop after the actual resume rebase, before the reserved tick continues.
        blob = (out/'slave.bin').read_bytes()[32:]
        begin = symbols['c3_resume']
        marker = bytes.fromhex('4cdf7fff44df4e75')
        end = blob.find(marker,begin,begin+256)
        assert end >= begin, 'resume epilogue missing'
        command('gdb', f'break *{base+end:#x}')
        command('gdb', 'monitor key 40 1')
        command('gdb','continue')
        reply = command('gdb','p/x $pc')
        pc = re.search(r'\$\d+\s*=\s*(0x[0-9a-fA-F]+)',reply)
        assert pc and int(pc[1],16)==base+end, reply
        command('gdb','monitor key 40 0')
        exact = snapshot(name+'-rebase', picture=False)
        assert exact['c2_in_tick'] == exact['c2_draw_mode'] == 1, exact
        assert exact['clock']['credit'] == exact['clock']['phase'] == exact['clock']['batch'] == 0, exact
        assert exact['c3_suspended'] == 0 and exact['c3_excluded'] >= held['c3_excluded']+250, exact
        assert exact['clock']['ticks'] == held['clock']['ticks'], exact
        timing = out/(name+'-sound.bin')
        command('gdb', f'dump binary memory {timing} {bases[0]+0x125a:#x} {bases[0]+0x1260:#x}')
        minimum, elapsed, work = struct.unpack('>3H',timing.read_bytes())
        assert minimum == elapsed and 6 <= minimum <= 8 and work == 0, (minimum,elapsed,work)
        assert exact['clock']['dropped'] == held['clock']['dropped'], exact
        command('gdb','delete breakpoints')
        fields(75)
        b = snapshot(name+'-resumed')
        assert b['c3_suspended'] == 0 and b['clock']['ticks'] > exact['clock']['ticks'], b
        return b
    snapshot('entry')
    if args.modal != 'race':
        fields(400)
    if args.modal == 'pause':
        a = pause('live')
        resume('live',a)
        a = pause('again')
        resume('again',a)
    elif args.modal == 'pit':
        assert args.route in ('practice','qualifying')
        a = snapshot('pit-before')
        command('gdb','monitor input JOY2_UP 1')
        fields(100)
        command('gdb','monitor input JOY2_UP 0')
        b = snapshot('accelerated-held')
        assert b['c3_reconstructions'] == a['c3_reconstructions']+1 and b['c3_suspended'] == 1, b
        fields(250)
        c = snapshot('accelerated-later')
        assert c['clock'] == b['clock'] and c['cars_sha256'] != b['cars_sha256'], (b,c)
        command('gdb','monitor input JOY2_UP 1')
        fields(50)
        command('gdb','monitor input JOY2_UP 0')
        d = snapshot('accelerated-return')
        assert d['c3_suspended'] == 0 and d['c3_excluded'] >= b['c3_excluded']+250, d
    elif args.modal in ('menu','pause-menu'):
        if args.modal == 'pause-menu':
            pause('before-menu')
        command('tap','45')
        for n in range(120):
            fields(25)
            command('shot', str(out/'menu-wait.png'))
            img = Image.open(out/'menu-wait.png').convert('RGB')
            dy = 10 if args.ntsc else 0
            if (img.getpixel((200,210+dy)) == (204,0,0)
                    and img.getpixel((190,255+dy)) == (102,119,153)):
                break
        else:
            raise AssertionError('frozen menu not reached')
        a = snapshot('menu-start')
        assert a['c2_mode'] == a['c2_in_tick'] == a['c2_hud_count'] == 0, a
        fields(250)
        b = snapshot('menu-held')
        assert b['clock'] == a['clock'] and b['cars_sha256'] == a['cars_sha256'] and b['session_sha256'] == a['session_sha256'], (a,b)
        if args.modal == 'pause-menu':
            command('gdb', f'break *{base+symbols["c3_pause_begin"]:#x}')
        command('menuclick','395','214')
        if args.modal == 'pause-menu':
            command('gdb','continue')
            reply = command('gdb','p/x $pc')
            pc = re.search(r'\$\d+\s*=\s*(0x[0-9a-fA-F]+)',reply)
            assert pc and int(pc[1],16)==base+symbols['c3_pause_begin'],reply
            command('gdb','delete breakpoints')
            fields(25)
            snapshot('returned-paused')
            command('tap','40')
        for n in range(120):
            fields(25)
            c = snapshot(f'return-{n}')
            if c['c2_mode'] == 1 and not c['c3_inactive']:
                break
        else:
            raise AssertionError('cockpit did not return')
        assert c['c2_mode'] == 1 and c['c3_epochs'] == b['c3_epochs']+1, c
        assert c['clock']['dropped'] == 0, c
    elif args.modal == 'replay':
        pause('live')
        command('tap','13')
        fields(50)
        a = snapshot('replay-entry')
        assert a['c2_mode'] == 2, a
        b = pause('replay')
        resume('replay', b)
        # Replay naturally returns to live pause after consuming its native tape.
        for _ in range(120):
            fields(50)
            a = snapshot(f'replay-progress-{_}')
            if a['c2_mode'] == 0:
                break
        else:
            raise AssertionError('replay did not finish')
        command('tap','40')
        fields(100)
        a = snapshot('live-return')
        assert a['c2_mode'] == 1 and a['clock']['dropped'] == 0, a
    elif args.modal == 'race':
        seen = set()
        for n in range(400):
            fields(25 if 'green' not in seen else 250)
            name = f'race-{n:03d}'
            command('shot', str(out/(name+'.png')))
            img = Image.open(out/(name+'.png')).convert('RGB')
            for state in ('green','viewing','results'):
                if showing(img,state) and state not in seen:
                    snapshot(state)
                    seen.add(state)
            if 'results' in seen:
                break
        else:
            raise AssertionError('no race results')
        assert {'green','viewing','results'} <= seen, seen
        a = snapshot('results-start')
        fields(250)
        b = snapshot('results-held')
        assert b['c2_mode'] == b['c2_in_tick'] == 0 and a['clock'] == b['clock'], (a,b)
    meta['modal']['status'] = 'PASS'
    (out/'modal.json').write_text(json.dumps(meta['modal'], indent=2)+'\n')
