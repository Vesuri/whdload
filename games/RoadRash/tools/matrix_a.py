#!/usr/bin/env python3
"""Sequential machine checks with per-cell deadlines, retained failures and scoped cleanup."""
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from rr import run_dir  # noqa: E402
CELLS=['a500-1m','a1200','a1200-fast','a1200-fast+cache','a1200-fast+nocache',
       '030-50','030-50+cache','040-25','040-25+cache','060-50','060-50+cache','040-mmu','060-mmu']

def config(cell):
    if cell not in CELLS:raise ValueError(cell)
    env=dict(os.environ)
    for key in ('AMIGA_SETUP','CPU','AMIGA_MODEL','CHIP_KB','FAST_KB','SLOW_KB','KICKSTART','EXTRA_ARGS','WHD_ARGS'):
        env.pop(key,None)
    env['WHD_ARGS']='Cache' if cell.endswith('+cache') else 'NoCache' if cell.endswith('+nocache') else ''
    if cell=='a500-1m':env['AMIGA_SETUP']=''
    elif cell.startswith('a1200'):env['AMIGA_SETUP']=cell.split('+')[0]
    elif cell.endswith('-mmu'):
        env.update(AMIGA_SETUP='a1200-'+cell[:3],WHD_ARGS='MMU',
                   SLAVE=str(Path(env.get('RR_BUILD_DIR',ROOT/'tmp/build'))/'RoadRash-verify-mmu.slave'),
                   EXTRA_ARGS='--uae_cpu_data_cache=false --uae_uaeboard=full',
                   RR_EXPECT_CPU='68'+cell[:3],RR_EXPECT_MMU='68'+cell[:3])
    else:
        cpu=cell[:3];freq=25000000 if cpu=='040' else 50000000
        share=Path(env.get('AMIGA_SHARE',Path.home()/'.local/share/amiga'))
        env.update(AMIGA_SETUP='',AMIGA_MODEL='A1200',KICKSTART=str(share/'Kickstarts/kick40068.A1200'),
                   CHIP_KB='2048',FAST_KB='8192',SLOW_KB='0',CPU='68EC030' if cpu=='030' else '68'+cpu+'-NOMMU',
                   EXTRA_ARGS=f'--uae_mmu_model=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency={freq} --uae_cpu_cycle_exact=true --uae_chipset=aga',
                   RR_EXPECT_CPU='68'+cpu,RR_EXPECT_MMU='0')
    env['WHD_ARGS']+=' '+os.environ.get('RR_WHD_EXTRA','')
    return env

def cleanup(out):
    p=run_dir(out)/'fsuae.pid'
    if p.exists():
        try:os.kill(int(p.read_text()),signal.SIGKILL)
        except ProcessLookupError:pass

def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('cells',nargs='*');ap.add_argument('--deadline',type=int,default=180)
    ap.add_argument('--normal',action='store_true')
    args=ap.parse_args();root=Path(args.out).resolve();root.mkdir(parents=True,exist_ok=True)
    results=[]
    selected=args.cells or [c for c in CELLS if not args.normal or not c.endswith('-mmu')]
    if args.normal and any(c.endswith('-mmu') for c in selected):raise ValueError('MMU functional cells require the diagnostic TC snapshot, not --normal')
    for cell in selected:
        out=root/cell
        if out.exists():raise RuntimeError(f'refusing to overwrite {out}')
        out.mkdir();start=time.monotonic()
        with (out/'run.log').open('w') as log:
            p=subprocess.Popen([sys.executable,str(ROOT/'tools/check_a.py'),str(out)]+(['--normal'] if args.normal else []),env=config(cell),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                rc=p.wait(timeout=args.deadline);status='passed' if rc==0 else 'failed'
            except subprocess.TimeoutExpired:
                status='timeout';rc=None;os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
            finally:cleanup(out)
        result=dict(cell=cell,status=status,returncode=rc,seconds=round(time.monotonic()-start,2),timing_comparable=not cell.endswith('-mmu'))
        if (out/'result.json').exists():
            data=json.loads((out/'result.json').read_text());result.update(fps=data['fps'] if result['timing_comparable'] else None,distance490=data['distance490'],race_cacr=data['after']['race_cacr'] if data['after'] else None)
        results.append(result);(root/'matrix.json').write_text(json.dumps(results,indent=2)+'\n');print(result,flush=True)
    if any(x['status']!='passed' for x in results):sys.exit(1)

if __name__=='__main__':main()
