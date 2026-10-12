#!/usr/bin/env python3
"""Functional and instrumentation preflight; never labels unsupported timing a baseline."""
import argparse,hashlib,json,os,re,subprocess,time
from pathlib import Path
import _amigaxdev
from amigaxdev.gdbserve import Server
from amigaxdev import barto
from cd32_runtime import ROOT,BASE,locate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True);p.add_argument('--machine',required=True,
        choices=['a1200-fast','a1200-030','a1200-040','a1200-060'])
    p.add_argument('--options',default='');a=p.parse_args()
    out=(ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    if os.environ.get('EXTRA_ARGS'):raise ValueError('fixed preflight configuration required')
    out.mkdir(parents=True);os.chdir(ROOT)
    run='../'+str(out.relative_to(ROOT))+'/run'
    env=dict(os.environ,FSUAE_RUN=run,AMIGA_SETUP=a.machine,SLAVE='',
        WHD_ARGS='CUSTOM5=0 '+a.options,INTRO_STOCK_CLOCK='1' if a.machine=='a1200-fast' else '0',
        WARP='0',NTSC='0',WINDOW='front',JOY0='none',JOY1='none',DETERMINISTIC='1')
    for key in ('WC_OBSERVER_CONFIG','WC_OBSERVER_OUTPUT','WC_MATRIX_CONFIG','WC_MATRIX_DIR'):env.pop(key,None)
    g=None
    def command(text,timeout=60):return g.cmd(text,timeout=timeout)
    try:
        g=Server('wc-matrix-probe',root=str(ROOT),run_dir='amiga/'+run,profile_window=False).boot(env)
        boot_config=command('monitor wc-audit')
        if 'WC_CPU ' not in boot_config:raise ValueError('capability command unavailable')
        for attempt in range(45):
            g.cont();time.sleep(1);g.stop()
            memory=out/f'calibration-{attempt}.bin'
            command(f'dump binary memory {memory.relative_to(ROOT)} {BASE:#x} {BASE+0x800000:#x}')
            try:layout=locate(memory.read_bytes())
            except ValueError:continue
            break
        else:raise TimeoutError('live patched game not found')
        h0=layout['hunks'][0]
        pc=h0+0x1fdd6
        answer=command(f'break *{pc:#x}\ncontinue\ndelete',600)
        if 'Breakpoint' not in answer or f'0x{pc:x}' not in command('info registers pc'):raise ValueError('credits not reached')
        live=command('monitor wc-audit');(out/'registers.txt').write_text(command('info registers'))
        if 'profile-window 00000000 7fffffff' not in command('monitor trace-window-all'):raise ValueError('PC window unavailable')
        aprof=command('monitor aprof start')
        enabled='E01' not in aprof and 'E02' not in aprof and 'error' not in aprof.lower()
        trace=out/'credits.bin'
        answer=command(f'monitor profile 5 "" "{trace}"',180)
        if enabled:
            stopped=command(f'monitor aprof stop {out}/credits.aprof')
            if not (out/'credits.aprof').exists():raise ValueError('aprof stop failed: '+stopped)
        t=barto.load(str(trace))
        pcs=[pc for f in t.fields for pc,cost,regs in t.instructions(f) if pc not in (None,0x7fffffff)]
        (out/'credits.png').write_bytes(t.fields[-1].shot)
        boot=next((out/'run').glob('boot.*'))
        result=dict(layout,machine=a.machine,options=a.options,complete=True,boot_cpu=boot_config,live_cpu=live,
                    aprof_reply=aprof,aprof_supported=enabled,fields=len(t.fields),instruction_records=len(pcs),
                    game_instruction_records=sum(h0<=pc<h0+0x35ea4 for pc in pcs),
                    publications=pcs.count(h0+0x3378e),vbls=pcs.count(h0+0x34162),
                    slave_sha256=hashlib.sha256((boot/'dh1/WingCommanderCD32/WingCommanderCD32.Slave').read_bytes()).hexdigest(),
                    emulator_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest())
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    finally:
        if g:g.p.kill()
        subprocess.run(['/bin/bash','amiga/run.sh','stop'],env=env,check=True)

if __name__=='__main__':main()
