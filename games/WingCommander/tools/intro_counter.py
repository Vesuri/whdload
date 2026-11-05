#!/usr/bin/env python3
"""Independent SWAP_ONLY check using read-only GDB breakpoints, not the host ledger."""
import argparse,hashlib,json,os,subprocess,re
from pathlib import Path
import _amigaxdev
import wc_run
from cd32_runtime import ROOT
from intro_capture import check_clock


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--layout',required=True)
    p.add_argument('--fields',type=int,default=20);a=p.parse_args()
    out=(ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists() or not 2<=a.fields<=100:raise ValueError('new tmp output and 2..100 fields required')
    if os.environ.get('EXTRA_ARGS'):raise ValueError('EXTRA_ARGS is not allowed')
    if any(c.isspace() for c in str(out.relative_to(ROOT))):raise ValueError('scratch name cannot contain whitespace')
    os.chdir(ROOT)
    out.mkdir(parents=True);h=json.loads((ROOT/a.layout).read_text())['hunks'];run='../'+str(out.relative_to(ROOT))+'/run'
    env=wc_run.run_env(out, WARP='0',NTSC='0',WINDOW='front',JOY0='none',JOY1='none',DETERMINISTIC='1',AMIGA_SETUP='a1200-fast',WHD_ARGS='CUSTOM5=0',SLAVE='',INTRO_STOCK_CLOCK='1')
    for key in ('WC_OBSERVER_CONFIG','WC_OBSERVER_OUTPUT'):env.pop(key,None)
    g=None
    try:
        g=wc_run.server('wc-counter', env, profile_window=False).boot(env)
        check_clock(out)
        for pc in (h[3]+0xee0,h[0]+0x3379a):
            answer=g.cmd(f'break *{pc:#x}\ncontinue\ndelete',timeout=600)
            if 'Breakpoint' not in answer or f'0x{pc:x}' not in g.cmd('info registers pc'):raise ValueError('anchor missed')
        vbl,swap=h[0]+0x34162,h[0]+0x3378e
        script=f'''break *{vbl:#x}
break *{swap:#x}
set $wc_field = -1
while $wc_field < {a.fields}
continue
if $pc == {vbl:#x}
set $wc_field = $wc_field + 1
printf "VBL %d %u\\n", $wc_field, *(unsigned int*){h[1]+0x7f02:#x}
else
printf "SWAP %d %u\\n", $wc_field, *(unsigned int*){h[1]+0x7f02:#x}
end
end
delete'''
        (out/'counter.gdb').write_text(script+'\n')
        raw=g.cmd(script,timeout=300);(out/'counter.txt').write_text(raw+'\n')
        if any(x in raw for x in ('Error','Remote connection closed','Cannot access')):raise ValueError(raw)
        vbls=[tuple(map(int,m)) for m in re.findall(r'^VBL (\d+) (\d+)$',raw,re.M)]
        swaps=[tuple(map(int,m)) for m in re.findall(r'^SWAP (-?\d+) (\d+)$',raw,re.M)]
        if len(vbls)!=a.fields+1 or [x[0] for x in vbls]!=list(range(a.fields+1)):raise ValueError('incomplete VBL interval')
        counts=[sum(f==i for f,c in swaps) for i in range(a.fields)]
        if not sum(counts):raise ValueError('no publications')
        result=dict(cpu_multiplier=4,cpu_frequency=0,fields=a.fields,counts=counts,vbls=vbls,swaps=swaps,complete=True)
        boot=wc_run.drawer(env)
        result['slave_sha256']=hashlib.sha256((boot/'WingCommanderCD32.Slave').read_bytes()).hexdigest()
        result['emulator_sha256']=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest()
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    finally:
        if g:g.p.kill()
        wc_run.stop(env)

if __name__=='__main__':main()
