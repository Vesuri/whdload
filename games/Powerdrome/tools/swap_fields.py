#!/usr/bin/env python3
"""Count frame completions over PAL fields with read-only debugger breakpoints.
Independent validation of the instruction-trace frame marker.
Only debugger convenience variables change; target memory/registers are read-only.
"""
import argparse
import os
from pathlib import Path
import re
import socket
import struct
from powerdrome import SOCK, send_request
from powerdrome_report import regions


def command(text):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(600)
        client.connect(SOCK)
        send_request(client, 'gdb '+text)
        chunks=[]
        while data := client.recv(65536): chunks.append(data)
        return b''.join(chunks).decode()

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('fields', type=int)
p.add_argument('out', type=Path)
p.add_argument('dump', type=Path)
p.add_argument('base', type=lambda x: int(x, 0))
p.add_argument('--marker', type=lambda x: int(x, 0), default=0x1067e)
a = p.parse_args()
assert a.fields > 1
code = a.dump.read_bytes()
r = {name: (lo, hi) for lo, hi, name, origin in regions(code, a.base, (a.out/'chip.bin').read_bytes())}
# The game installs a VBL server at 5684. The default marker counts the title
# inset; bc7c counts normal driving presentations. No guest writes.
vbl = r['game'][0]+0x5684
swap = r['game'][0]+a.marker
probes = [int(x, 0) for x in os.environ.get('COVERAGE_PROBES', '').split()]
assert len(probes) == len(set(probes)) and a.marker not in probes and 0x5684 not in probes
probe_breaks = ''.join(f'break *{r["game"][0]+x:#x}\n' for x in probes)
probe_tests = ''.join(f'if $pc == {r["game"][0]+x:#x}\nprintf "PDEVENT %d {x:#x}\\n", $pd_field\nend\n' for x in probes)
state = r['game'][0] + 0xa6e
state_offsets = [0xbe, 0x5c, 0x11e, 0x138, 0x194, 0x1ba, 0x2ea, 0x2f2, 0x4ce, 0x4d0, 0xaa, 0xe6, 0xfc, 0xf6]
state_probe = ''
if os.environ.get('COVERAGE_STATE') == '1':
    values = ', '.join(f'*(unsigned short*){state+x:#x}' for x in state_offsets)
    state_probe = 'printf \"PDSTATE %d ' + ' '.join(['%u']*len(state_offsets)) + '\\n\", $pd_field, ' + values + '\n'
# Optional timing samples are read-only and use the same completed-frame marker.
if os.environ.get('TIMING_STATE') == '1':
    early = os.environ.get('TIMING_EARLY') == '1'
    live_frame = None
    if early:
        chip = (a.out/'chip.bin').read_bytes()
        patch = r['game'][0] + 0xca44
        assert struct.unpack_from('>H', chip, patch)[0] == 0x4ef9, 'Early timing capture needs installed C3 hooks'
        live_frame = struct.unpack_from('>I', chip, patch+2)[0] - a.base
        assert 0 <= live_frame < len(code)

    def timing_locations(tag, initialized):
        hits = [m.start() for m in re.finditer(tag, code)]
        if early:
            # The installed JMP selects the live relocated slave before its
            # counters initialize. Its first following tag is authoritative;
            # stale loader copies elsewhere are never selected by zero values.
            hits = [off for off in hits if live_frame < off < live_frame+16384]
            return [min(hits)] if hits else []
        return [off for off in hits if initialized(off)]
    timing_words = [0x21c, 0x194, 0x1ba, 0x11e, 0x12c, 0x12e, 0x130,
                    0x11a, 0x138, 0x45a, 0x196, 0x198, 0x4ce, 0x4d2,
                    0x4c6, 0x1e0, 0x1e6, 0x432, 0x42a, 0x42e]
    vals = [f'*(unsigned int*){r["game"][0]+0xf96:#x}',
            f'*(unsigned int*){state+0x5e:#x}']
    vals += [f'*(unsigned short*){state+x:#x}' for x in timing_words]
    state_probe += 'printf "PDTIME %d ' + ' '.join(['%u']*len(vals)) + '\\n", $pd_field, ' + ', '.join(vals) + '\n'
    # Private logical input state is read-only evidence of event ownership.
    active_inputs=timing_locations(b'PDINPT02', lambda off: struct.unpack_from('>I',code,off+12)[0])
    assert len(active_inputs)<=1, 'Ambiguous initialized logical input state'
    input_sample=''
    if active_inputs:
        ip=a.base+active_inputs[0]
        offsets=[(12,'int'),(28,'int'),(44,'short'),(46,'short'),(48,'short'),
                 (52,'short'),(56,'short')]
        inputs=[f'*(unsigned {kind}*){ip+off:#x}' for off,kind in offsets]
        input_sample='printf "PDINPUT_EVENT %d {off} ' + ' '.join(['%u']*len(inputs)) + '\\n", $pd_field, ' + ', '.join(inputs) + '\n'
    engines=timing_locations(b'PDENGN01', lambda off: struct.unpack_from('>I',code,off+16)[0])
    assert len(engines)<=1
    engine_sample=''
    if engines:
        ep=a.base+engines[0]
        periodic=timing_locations(b'PDTIME01', lambda off: struct.unpack_from('>H',code,off+8)[0])
        assert len(periodic)==1 and active_inputs
        epvals=[f'*(unsigned int*){ip+12:#x}',
                f'*(unsigned short*){a.base+periodic[0]+46:#x}']
        epvals += [f'*(unsigned {kind}*){ep+off:#x}' for off,kind in
                   ((8,'short'),(16,'int'),(20,'int'),(24,'int'),(28,'int'),(32,'int'))]
        epvals += [f'*(unsigned short*){state+off:#x}' for off in
                   (0x196,0x198,0x138,0x454,0xe4,0x194)]
        epvals.append(f'*(unsigned short*){ep+10:#x}')
        engine_sample='printf "PDENGINE_EVENT %d {off} ' + ' '.join(['%u']*len(epvals)) + '\\n", $pd_field, ' + ', '.join(epvals) + '\n'
    heat=timing_locations(b'PDHEAT02', lambda off: struct.unpack_from('>H',code,off+8)[0]==1)
    assert len(heat)<=1
    heat_sample=''
    if heat:
        assert active_inputs
        hp=a.base+heat[0]
        hpvals=[f'*(unsigned int*){ip+12:#x}',f'*(unsigned int*){hp+16:#x}',
                f'*(unsigned short*){hp+12:#x}', '$d0 & 65535',
                f'*(unsigned short*){state+0x196:#x}',f'*(unsigned short*){state+0x198:#x}']
        heat_sample='printf "PDHEAT_EVENT %d {off} ' + ' '.join(['%u']*len(hpvals)) + '\\n", $pd_field, ' + ', '.join(hpvals) + '\n'
    movement_clocks=[m.start() for m in re.finditer(b'PDMCLK0[12]',code)
                     if struct.unpack_from('>H',code,m.start()+8)[0]==1]
    assert len(movement_clocks)<=1
    movement_clock_sample=''
    if movement_clocks:
        mp=a.base+movement_clocks[0]
        mv=[f'*(unsigned {kind}*){mp+off:#x}' for off,kind in
            ((12,'int'),(16,'int'),(20,'short'),(24,'int'),(28,'int'))]
        if code[movement_clocks[0]:movement_clocks[0]+8]==b'PDMCLK02':
            mv.append(f'*(unsigned short*){mp+32:#x}')
        movement_clock_sample='printf "PDMCLK_EVENT %d ' + ' '.join(['%u']*len(mv)) + '\\n", $pd_field, ' + ', '.join(mv) + '\n'
    worlds=timing_locations(b'PDWORLD1', lambda off: struct.unpack_from('>I',code,off+20)[0])
    assert len(worlds)<=1
    world_sample=''
    if worlds:
        wp=a.base+worlds[0]
        wv=[f'*(unsigned {kind}*){wp+off:#x}' for off,kind in
            ((8,'short'),(16,'int'),(20,'int'))]
        wv += [f'*(unsigned short*){state+x:#x}' for x in
               (0x21c,0x194,0x11e,0x12c,0x12e,0x130,0x138,0x196,0x198,0x62)]
        world_sample='printf "PDWORLD_EVENT %d {off} ' + ' '.join(['%u']*len(wv)) + '\\n", $pd_field, ' + ', '.join(wv) + '\n'
    fast_worlds=timing_locations(b'PDW20T01', lambda off: struct.unpack_from('>H',code,off+8)[0]==1)
    assert len(fast_worlds)<=1
    fast_world_sample=''
    if fast_worlds:
        fp=a.base+fast_worlds[0]
        fv=[f'*(unsigned {kind}*){fp+off:#x}' for off,kind in
            ((12,'int'),(16,'int'),(20,'int'),(10,'short'))]
        fv += [f'*(unsigned int*){ip+12:#x}',f'*(unsigned int*){state+0x1a2:#x}',
               f'*(unsigned short*){state+0x1e0:#x}',f'*(unsigned short*){state+0xe4:#x}']
        fast_world_sample='printf "PDW20_EVENT %d {off} ' + ' '.join(['%u']*len(fv)) + '\\n", $pd_field, ' + ', '.join(fv) + '\n'
    integrators=[m.start() for m in re.finditer(b'PDW20I01',code)]
    integrator_sample=''
    if fast_worlds:
        # The integrator follows PDW20T01 in this explicit prototype; choose the
        # live copy in the same relocated slave, not an old loader buffer.
        candidates=[pos for pos in integrators if 0<pos-fast_worlds[0]<2048]
        if candidates:
            assert len(candidates)==1
            rp=a.base+candidates[0]
            rv=[f'*(unsigned short*){rp+8:#x}']
            rv += [f'*(unsigned int*){rp+off:#x}' for off in (12,16,20)]
            integrator_sample='printf "PDR20_EVENT %d {off} ' + ' '.join(['%u']*len(rv)) + '\\n", $pd_field, ' + ', '.join(rv) + '\n'
    force_sample=''
    if fast_worlds:
        forces=[m.start() for m in re.finditer(b'PDW20F01',code)
                if 0<m.start()-fast_worlds[0]<4096]
        if forces:
            assert len(forces)==1
            force=a.base+forces[0]
            fv=[f'*(unsigned int*){fp+12:#x}']
            fv += [f'(unsigned int)${reg}' for reg in ('d0','d5','d6','d7','sp')]
            fv += [f'*(unsigned int*){state+0x1a2:#x}']
            fv += [f'*(unsigned short*){state+x:#x}' for x in
                   (0xe4,0x43a,0x24c,0x1e0,0x1e6,0x1e4,0x1da,0x1dc,0x1de)]
            fv += [f'*(unsigned short*){force+x:#x}' for x in (8,10,12,14,16,18)]
            fv += [f'*(unsigned int*){force+x:#x}' for x in (20,24,28,32,36)]
            fv += [f'*(unsigned short*)*(unsigned int*){r["game"][0]+0x5ca:#x}']
            force_sample='printf "PDFORCE_EVENT %d {off} ' + ' '.join(['%u']*len(fv)) + '\\n", $pd_field, ' + ', '.join(fv) + '\n'
    key_sample=''
    if fast_worlds:
        keys=[m.start() for m in re.finditer(b'PDKEY001',code)
              if 0<m.start()-fast_worlds[0]<4096]
        if keys:
            assert len(keys)==1
            kp=a.base+keys[0]
            kv=[f'*(unsigned int*){fp+12:#x}']
            kv += [f'*(unsigned short*){kp+x:#x}' for x in (8,10,12,14,16,18)]
            kv += [f'*(unsigned int*){kp+x:#x}' for x in (20,24,28,32)]
            kv += [f'*(unsigned short*){state+x:#x}' for x in (0xd2,0xd4,0x334,0x240)]
            key_sample='printf "PDKEY_EVENT %d {off} ' + ' '.join(['%u']*len(kv)) + '\\n", $pd_field, ' + ', '.join(kv) + '\n'
    session_sample=''
    if fast_worlds:
        sessions=[m.start() for m in re.finditer(b'PDSESS01',code)
                  if 0<fast_worlds[0]-m.start()<4096]
        if sessions:
            assert len(sessions)==1 and len(periodic)==1 and keys and engines
            sptr=a.base+sessions[0]
            tp=a.base+periodic[0]
            sv=[f'*(unsigned int*){sptr+x:#x}' for x in range(8,40,4)]
            sv += [f'*(unsigned {kind}*){tp+x:#x}' for x,kind in
                   ((8,'short'),(10,'short'),(12,'int'),(16,'int'),(44,'short'))]
            sv += [f'*(unsigned short*){wp+8:#x}', f'*(unsigned int*){fp+12:#x}',
                   f'*(unsigned int*){ip+12:#x}']
            sv += [f'*(unsigned short*){ip+x:#x}' for x in (8,10)]
            sv += [f'*(unsigned short*){kp+8:#x}']
            sv += [f'*(unsigned short*){ep+x:#x}' for x in (8,10,12,14)]
            session_sample='printf "PDSESSION_EVENT %d {off} ' + ' '.join(['%u']*len(sv)) + '\\n", $pd_field, ' + ', '.join(sv) + '\n'
    pit_sample=''
    initial_pit_sample=''
    if fast_worlds:
        pits=[m.start() for m in re.finditer(b'PDPIT001',code)
              if 0<fast_worlds[0]-m.start()<4096]
        if pits:
            assert len(pits)==1
            pitp=a.base+pits[0]
            pv=[f'*(unsigned short*){pitp+x:#x}' for x in (8,10)]
            pv += [f'*(unsigned int*){pitp+x:#x}' for x in range(12,60,4)]
            pv += [f'*(unsigned short*){pitp+60:#x}',f'*(unsigned short*){wp+26:#x}',f'*(unsigned short*){hp+12:#x}',f'*(unsigned int*){hp+16:#x}',f'*(unsigned short*){tp+46:#x}']
            pit_sample='printf "PDPIT_EVENT %d {off} ' + ' '.join(['%u']*len(pv)) + '\\n", $pd_field, ' + ', '.join(pv) + '\n'
            iv=[f'*(unsigned short*){pitp+62:#x}', f'*(unsigned int*){r["game"][0]+0x48fe:#x}']
            iv += [f'*(unsigned short*){state+x:#x}' for x in (0xda,0xdc,0xbe)]
            initial_pit_sample='printf "PDINITIAL_EVENT %d {off} ' + ' '.join(['%u']*len(iv)) + '\\n", $pd_field, ' + ', '.join(iv) + '\n'
    pit_opponent_sample=''
    if fast_worlds:
        popps=[m.start() for m in re.finditer(b'PDPOPP01',code)
               if 0<fast_worlds[0]-m.start()<4096]
        if popps:
            assert len(popps)==1
            op=a.base+popps[0]
            ov=[f'*(unsigned short*){op+x:#x}' for x in (8,10,12,14)]
            ov += [f'*(unsigned int*){op+x:#x}' for x in range(16,44,4)]
            ov += [f'*(unsigned short*){op+44:#x}']
            ov += [f'*(unsigned int*){op+x:#x}' for x in (48,52,56)]
            ov += [f'*(unsigned short*){state+0x21c:#x}',f'*(unsigned short*){wp+26:#x}',f'*(unsigned short*){state+0x62:#x}',f'*(unsigned int*){state+0x5e:#x}', '(unsigned int)$d0', '(unsigned int)$d7']
            ov += [f'*(unsigned short*){op+x:#x}' for x in (64,66,132)]
            ov += [f'*(unsigned short*){wp+8:#x}', f'*(unsigned int*){fast_worlds[0]+a.base+12:#x}', '(unsigned int)$d5']
            pit_opponent_sample='printf "PDPOPP_EVENT %d {off} ' + ' '.join(['%u']*len(ov)) + '\\n", $pd_field, ' + ', '.join(ov) + '\n'
    retune_sample=''
    if fast_worlds:
        retunes=[m.start() for m in re.finditer(b'PDRETUNE',code)
                 if 0<fast_worlds[0]-m.start()<4096]
        if retunes:
            assert len(retunes)==1
            rp=a.base+retunes[0]
            rv=[f'*(unsigned {kind}*){rp+x:#x}' for x,kind in
                ((8,'short'),(10,'short'),(12,'int'),(16,'short'),(20,'int'),(24,'int'),(18,'short'),(28,'short'),(32,'int'),(36,'int'),(40,'int'))]
            retune_sample='printf "PDRETUNE_EVENT %d {off} ' + ' '.join(['%u']*len(rv)) + '\\n", $pd_field, ' + ', '.join(rv) + '\n'
    # Keep event samples separate from presentation samples used by timing_report.
    for off in probes:
        sample = 'printf "PDTIME_EVENT %d ' + hex(off) + ' ' + ' '.join(['%u']*len(vals)) + '\\n", $pd_field, ' + ', '.join(vals) + '\n'
        sample += input_sample.replace('{off}',hex(off))
        sample += session_sample.replace('{off}',hex(off))
        sample += pit_sample.replace('{off}',hex(off))
        sample += initial_pit_sample.replace('{off}',hex(off))
        sample += retune_sample.replace('{off}',hex(off))
        sample += pit_opponent_sample.replace('{off}',hex(off))
        if os.environ.get('OPPONENT_STATE') == '1' and off in (0xe976,0xca3e,0xcedc,0xe3c4,0xbc44,0xd7f0,0x14090,0xe8d4):
            # Four native records, all 190 bytes each. Guard the native count
            # and relocated bank before reading; never write game state.
            pointer=f'*(unsigned int*){state+0x342:#x}'
            count=f'*(short*){state+0x340:#x}'
            sample += f'if ({pointer} == {r["game"][0]+0x1ab0:#x} || {pointer} == {r["game"][0]+0x1da8:#x}) && {count} >= 0 && {count} <= 3\n'
            for opponent in range(4):
                words=[f'*(unsigned short*)({pointer}+{opponent*190+x})' for x in range(0,190,2)]
                sample += f'if {count} >= {opponent}\n'
                sample += f'printf "PDOPP_ARRAY %d {off:#x} {opponent} ' + '%04x'*95 + '\\n", $pd_field, ' + ', '.join(words) + '\nend\n'
            sample += 'end\n'
        if off in (0xd9a0,0xde0a,0xdfae,0xdffc,0xe0c0,0x10d0c,0x13514):
            sample += engine_sample.replace('{off}',hex(off))
        if off in (0xcfec,0xcff8):
            sample += heat_sample.replace('{off}',hex(off))
        if off in (0xccee,0xccf6,0x14090,0xe8d4,0x103a2,0xbfb0,0xbfb6,0x14764,0x147a6):
            contract_values=[f'(unsigned int)${reg}' for reg in
                             ('d0','d1','d2','d3','d4','d5','d6','d7','a0','a1','a2','a3','a4','a5','a6','sp','sr')]
            contract_values += [f'*(unsigned short*){state+x:#x}' for x in (0x21c,0x194)]
            sample += 'printf "PDMREG_EVENT %d ' + hex(off) + ' ' + ' '.join(['%u']*len(contract_values)) + '\\n", $pd_field, ' + ', '.join(contract_values) + '\n'
        if off in (0xccee,0xcd2c,0xcd3a,0xcde2):
            movement_values=[f'*(unsigned short*){state+x:#x}' for x in
                             (0x21c,0x194)]
            movement_values += [f'${reg} & 65535' for reg in ('d4','d5','d6','d7')]
            movement_values += [f'*(unsigned short*){state+x:#x}' for x in
                               (0x186,0x188,0x18a,0x12c,0x12e,0x130,0x1e0)]
            movement_values.append(f'*(unsigned int*){state+0x1a2:#x}')
            sample += 'printf "PDMOVE_EVENT %d ' + hex(off) + ' ' + ' '.join(['%u']*len(movement_values)) + '\\n", $pd_field, ' + ', '.join(movement_values) + '\n'
        if off in (0xcd2c,0xcd3a):
            sample += integrator_sample.replace('{off}',hex(off))
        if off==0xcd2c:
            sample += movement_clock_sample
        if off in (0xccee,0xcde2,0xcedc):
            sample += world_sample.replace('{off}',hex(off))
            sample += fast_world_sample.replace('{off}',hex(off))
        if off in (0xcd5c,0xcd64,0xcd96,0xcdc4,0xb390,0xb398,0xc59e,0xc5a6,0x9c8c,0x9c92,0xadba,0xadc0):
            sample += force_sample.replace('{off}',hex(off))
        if off in (0xccee,0xcd2c,0xcd3a,0xcedc,0x1003a,0x10046):
            sample += key_sample.replace('{off}',hex(off))
        if off==0xd9a0:
            # Native resource result in d1 immediately before committing it.
            offsets=[0x194,0x1ba,0x458,0x45a,0x44e,0x450,0xe4,0x240]
            resource_values=[f'*(unsigned short*){state+x:#x}' for x in offsets]
            sample += 'printf "PDRESOURCE %d ' + ' '.join(['%u']*9) + '\\n", $pd_field, ' + ', '.join(resource_values) + ', ($d1 & 65535)\n'
        probe_tests += f'if $pc == {r["game"][0]+off:#x}\n{sample}end\n'

setup = f'break *{vbl:#x}\nbreak *{swap:#x}\n{probe_breaks}set $pd_field = -1\n'
reply = command(setup)
logpath = a.out/'swaps-gdb.txt'
logpath.write_text(reply)
try:
    for end in range(min(100,a.fields), a.fields+100, 100):
        end=min(end,a.fields)
        part=command(f'''while $pd_field < {end}
continue
if $pc == {vbl:#x}
set $pd_field = $pd_field + 1
else
if $pc == {swap:#x}
printf "PDFRAME %d\\n", $pd_field
{state_probe}end
{probe_tests}end
end
''')
        # A GDB loop can abort without an uppercase ERROR. Query its actual
        # counter separately before claiming that this chunk completed.
        check=command('printf "PDWINDOW %d\\n", $pd_field')
        part+=check
        reply+=part
        with logpath.open('a') as log: log.write(part)
        assert 'ERROR' not in part, 'Debugger reported an error'
        reached=re.findall(r'^PDWINDOW (-?\d+)$',check,re.M)
        assert reached==[str(end)], f'Incomplete debugger field loop: expected {end}, observed {reached}'
        print(f'Counted {end}/{a.fields} PAL fields', flush=True)
        if end==a.fields: break
finally:
    command('delete')
(a.out/'swaps-gdb.txt').write_text(reply)
swaps = [0]*a.fields
for field in re.findall(r'^PDFRAME (-?\d+)$', reply, re.M):
    index = int(field)
    if 0 <= index < a.fields:
        swaps[index] += 1
assert 'ERROR' not in reply
first = next((i for i, n in enumerate(swaps) if n), None)
last = max((i for i, n in enumerate(swaps) if n), default=None)
assert first is not None and last > first, 'insufficient swaps for FPS'
frames = sum(swaps[first+1:last+1])
kind = 'Driving' if a.marker == 0xbc7c else 'demo'
report = (f'Read-only {kind} frame counter ({a.fields} PAL fields, marker {a.marker:#x})\n'
          f'{kind} frame completions per field: {"".join(str(n) for n in swaps)}\n'
          f'{frames} frames in {last-first} fields: {(last-first)/frames:.2f} fields/frame, '
          f'{50*frames/(last-first):.1f} fps (PAL)\n')
(a.out/'frames.txt').write_text(report)
print(report, end='')
