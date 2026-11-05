#!/usr/bin/env python3
"""Unskipped 10 Hz title and first credit page, using the slave frame recorder."""
import argparse, hashlib, json, os, re, shutil, struct, subprocess
from pathlib import Path
import _amigaxdev
import wc_run
from cd32_runtime import ROOT, BASE, locate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--layout',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--machine',choices=('a1200-030','a1200-040'),required=True)
    p.add_argument('--full-cycle',action='store_true')
    a=p.parse_args();out=a.output.resolve();build=a.build.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    meta=json.loads((build/'build.json').read_text());slave=build/'WingCommanderCD32.Slave'
    if not meta['release'] or not meta['frame_stats'] or hashlib.sha256(slave.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('intact diagnostic release required')
    sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
    layout=json.loads(a.layout.read_text());h=layout['hunks'];s=layout['slave']
    out.mkdir(parents=True);os.chdir(ROOT)
    pcs=[s+sy['release_presented'],h[0]+0x34162,s+sy['intro_world'],s+sy['intro_draw'],h[0]+0x1fdd6,h[0]+0x1fe38,h[0]+0x1fe48]
    cfg=out/'observer.cfg';cfg.write_text(' '.join(f'{x:x}' for x in [h[0],h[1],h[3]]+pcs)+'\n')
    env={k:v for k,v in os.environ.items() if not k.startswith(('WC_OBSERVER_','WC_MATRIX_','WC_STATE_'))}
    env = wc_run.run_env(out, env, SLAVE=str(slave),AMIGA_SETUP=a.machine,WARP='1',NTSC='0',
        WC_NOMMU_CORE='1' if a.machine=='a1200-040' else '0',INTRO_STOCK_CLOCK='0',WC_BASELINE_CACHE_MODEL='1',
        WHD_ARGS='CUSTOM5=0 NOWRITECACHE '+('NoMMU' if a.machine=='a1200-040' else 'CACHE DCACHE'),
        WINDOW='front',JOY0='none',JOY1='none',DETERMINISTIC='1',WC_INSTANT_BLITTER='0',
        WC_OBSERVER_CONFIG=str(cfg),WC_OBSERVER_OUTPUT=str(out/'events.txt'),
        WC_STATE_PC=f'{s+sy["intro_draw"]:x}',WC_STATE_OUTPUT=str(out/'states.bin'))
    g=None
    def cmd(text):
        r=g.cmd(text,timeout=600)
        if any(x in r for x in ('Cannot access','Error','Remote connection closed','No such file')):raise RuntimeError(r)
        return r
    def until(pc):
        r=cmd(f'break *{pc:#x}\ncontinue\ndelete')
        if 'Breakpoint' not in r or f'0x{pc:x}' not in cmd('info registers pc'):raise ValueError('missed checkpoint '+r)
    def dump(name,addr,size):
        f=out/name;cmd(f'dump binary memory {f.relative_to(ROOT)} {addr:#x} {addr+size:#x}');return f.read_bytes()
    def val(name,size=4):return int.from_bytes(dump('scratch.bin',s+sy[name],size),'big')
    def collect(label):
        dst=out/label;dst.mkdir()
        ptr=val('frame_stats_buffer');count=val('frame_stats_count');dc=val('frame_stats_display_count');hz=val('timing_hz');epoch=val('frame_stats_first')
        raw=dump('scratch.bin',ptr+16,4*count)
        (dst/'framestats.bin').write_bytes(struct.pack('>4sIII',b'WCFS',hz,count,0)+raw)
        raw=dump('scratch.bin',ptr+16+meta['frame_records']*4+16,dc*32)
        (dst/'displaystats.bin').write_bytes(struct.pack('>4sIII',b'WCDS',hz,dc,32)+raw)
        (dst/'result.json').write_text(json.dumps(dict(fixture=meta,machine=a.machine,timing_core=a.machine=='a1200-040',baseline_cache_model=True,custom5=0,options=env['WHD_ARGS'],ntsc=False,held_key=None,frame_epoch=epoch,complete=True,scope=label),indent=2)+'\n')
        shutil.copyfile(cfg,dst/'observer.cfg')
        return dict(records=count,pictures=dc,epoch=epoch)
    try:
        g=wc_run.server('wc-intro-clock', env, profile_window=False).boot(env)
        until(h[0]+0x1fd00)
        live=cmd('monitor wc-audit')
        memory=dump('title-start-fast.bin',BASE,0x800000)
        if locate(memory)!=layout:raise ValueError('layout changed')
        until(s+sy['intro_draw'])
        dump('title-ready-fast.bin',BASE,0x800000)
        until(h[0]+0x1fd96)
        title=collect('title')
        print('title completed; '+str(title),flush=True)
        until(h[0]+0x1fdda)
        dump('credits-start-fast.bin',BASE,0x800000)
        until(h[0]+0x1fe38)
        credits=collect('credits')
        dump('credits-end-fast.bin',BASE,0x800000)
        print('credit page completed; '+str(credits),flush=True)
        if a.full_cycle:
            until(h[0]+0x1fc8e)
            dump('cycle-end-fast.bin',BASE,0x800000)
        until(h[0]+0x1898a);cmd('monitor key 45 1')
        until(h[0]+0x20164);cmd('monitor key 45 0')
        until(h[0]+0x20214)
        dump('menu-fast.bin',BASE,0x800000)
        result=dict(complete=True,layout=layout,fixture=meta,machine=a.machine,live_cpu=live,title=title,credits=credits,full_cycle=a.full_cycle,
            emulator_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest())
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:
        if g:g.p.kill()
        wc_run.stop(env)
    for label in ('title','credits'):shutil.copyfile(out/'events.txt',out/label/'events.txt')

if __name__=='__main__':main()
