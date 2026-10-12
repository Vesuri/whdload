#!/usr/bin/env python3
"""Verify retained matrix cells and print a documentation table.

By default require every machine/route. --partial reports completed cells and
lists missing cells explicitly. No emulator is launched or modified.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import audit_hooks
from rate_matrix import MACHINES, ROUTES, CAPTURE_ROUTES, NATIVE_COMBAT_ROUTES, route_window
import native_scene_state
import simulation_latency
import simulation_rate
import sim60_state



def settings(folder, meta):
    """Check accepted UAE settings, independently of requested metadata."""
    log=(Path(folder)/'emulator-settings.log').read_text()
    options=dict(re.findall(r'Set option (\w+) = "([^"\n]*)"',log))
    # FS-UAE copies a shared startup log into its private log. Concurrent
    # boots can contaminate frontend "cpu ="/"ntsc_mode =" lines; the UAE
    # Set option records are written after switching to the private file.
    # PAL is the default; corroborate it with the observed Exec clock.
    if 'ntsc' not in options and meta['ntsc_mode']==0 and meta['observed_exec_hz']==50:
        options['ntsc']='false'
    expected=dict(cpu_model=meta['cpu'].replace('68EC020','68020').replace('-NOMMU',''),
                  cpu_speed='real',cpu_cycle_exact='true',
                  chipmem_size=str(meta['chip_kb']//512),
                  bogomem_size=str(meta['slow_kb']//256),
                  fastmem_size=str(meta['fast_kb']//1024),
                  ntsc='true' if meta['ntsc_mode'] else 'false')
    if 'NOMMU' in meta['cpu']:expected['mmu_model']='0'
    for option,value in re.findall(r'--uae_(\w+)=([^ ]+)',meta['extra_args']):
        expected[option]=value
    for key,value in expected.items():
        assert options.get(key)==value,(str(folder),key,options.get(key),value)
    assert meta['observed_exec_hz']==(60 if meta['ntsc_mode'] else 50)
    effective=Path(folder)/'emulator-effective.uae'
    if effective.exists():
        values=dict(re.findall(r'^(\w+)=([^\n]+)$',effective.read_text(),re.M))
        for key,value in expected.items():
            # UAE omits disabled MMU and may omit the multiplier. Explicit
            # fixed frequency, CPU model and timing options remain checked.
            if key=='mmu_model' and value=='0' and key not in values:continue
            if key=='cpu_multiplier' and key not in values:continue
            assert values.get(key)==value,(str(folder),'effective',key,values.get(key),value)
    return {key:options.get(key) for key in (*expected,'blitter_cycle_exact','waiting_blits','immediate_blits')}


def inspect(prefix, partial=False, routes=None):
    routes = list(ROUTES) if routes is None else routes
    rows = []
    missing = []
    for machine in MACHINES:
        for route in routes:
            name = machine+'-'+route
            path = prefix/(name+'.json')
            if not path.exists():
                missing.append(name)
                continue
            report = json.loads(path.read_text())
            config = report['config']
            assert config['machine'] == machine and config['route'] == route
            folder = prefix/name
            binary = (folder/'slave.slave').read_bytes()
            assert hashlib.sha256(binary).hexdigest() == report['slave_sha256']
            assert binary == (prefix/(name+'.slave')).read_bytes()
            meta = json.loads((folder/'metadata.json').read_text())
            settings(folder,meta)
            for key in ('cpu','chip_kb','fast_kb','slow_kb','ntsc_mode','extra_args'):
                assert meta[key] == config[key], (name,key)
            assert meta['whd_args'].split().count('CUSTOM5=1') == 1
            assert meta['whd_args'].strip() == ('CUSTOM5=1 '+config['whd_args']).strip()
            native = route.startswith('native-')
            assert meta['verify_flags'] == config['flags'], (name, 'build flags')
            start, end, _, checkpoints = route_window(route, config.get('substeps') or 12)
            if 'start' in config:
                assert (config['start'],config['end'],config['checkpoints']) == (start,end,checkpoints)
            assert meta['frame' if native else 'tick'] == start, (name, 'capture boundary')
            events = json.loads((folder/'field-events.json').read_text())
            assert events['field_hz'] == meta['observed_exec_hz'] == meta['field_hz']
            assert events['fields'] == 100
            for values in events['events'].values():
                assert values == sorted(values)
                assert all(0 <= value < events['fields'] for value in values)
            assert events['events']['update_starts'], (name,'update-start observations missing')
            latency = simulation_latency.inspect_fields(folder)
            if native:
                if route in NATIVE_COMBAT_ROUTES:
                    native_scene_state.inspect(folder, prefix/(name+'.lst'), 'boss' if route == 'native-boss' else 'type10')
                points = events['events']['presentations']
                span = points[-1]-points[0] if len(points)>1 else 0
                fps = (len(points)-1)*events['field_hz']/span if span else None
                updates = len(events['events']['updates'])*events['field_hz']/events['fields']
                assert fps == report['measurement']['presentation_hz']
                assert updates == report['measurement']['updates_hz']
                growth = None
            else:
                measured = simulation_rate.interval(folder,folder/'checkpoints'/str(end))
                assert sim60_state.read(folder)['substeps'] == (config.get('substeps') or 12), name
                if route == 'type10-heavy':
                    boundaries = [folder]+[folder/'checkpoints'/str(tick) for tick in checkpoints]
                    measured['segments'] = [simulation_rate.interval(a,b)
                                            for a,b in zip(boundaries,boundaries[1:])]
                assert measured == report['measurement'], name
                audit_hooks.installed(folder,prefix/(name+'.lst'))
                fps = measured['presentation_hz']
                updates = measured['updates_hz']
                growth = measured['pending_growth']
            rows.append(dict(machine=machine,route=route,updates_hz=updates,
                             presentations_hz=fps,pending_growth=growth,
                             largest_update_gap_fields=latency['updates']['largest_complete_gap_fields']))
    if missing and not partial:
        raise ValueError('Incomplete matrix: '+', '.join(missing))
    return rows,missing


def render(rows,missing):
    lines = ['| Machine | Route | Updates/s | Presentations/s | Pending growth | Largest observed update-start gap (fields) |',
             '|---|---|---:|---:|---:|---:|']
    def number(value):
        return '—' if value is None else f'{value:.3f}' if isinstance(value,float) else str(value)
    for row in rows:
        lines.append('| '+' | '.join(number(row[k]) for k in
                     ('machine','route','updates_hz','presentations_hz','pending_growth','largest_update_gap_fields'))+' |')
    lines.append('')
    lines.append('SIM60 rates use completed-tick endpoints; native presentations use complete inter-presentation intervals in a 100-field window. Gap values are window-local, not game-wide maxima. Pending growth is not applicable to native timing.')
    if missing:
        lines += ['',f'Incomplete: {len(missing)} cells remain: '+', '.join(missing)+'.']
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix',type=Path)
    parser.add_argument('--partial',action='store_true')
    parser.add_argument('--routes',nargs='+',choices=CAPTURE_ROUTES,default=list(ROUTES))
    args = parser.parse_args()
    print(render(*inspect(args.prefix,args.partial,args.routes)))
