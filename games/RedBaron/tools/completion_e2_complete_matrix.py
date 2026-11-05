"""Sequential feature A/B pairs; no parallel emulators or automatic retries."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
os.environ.update(BENCH_DEVELOPER='1',BENCH_BATCH_KEYS='1')
root=Path('tmp/prof')
for machine,mask in [('060',0x32ffa),('040',0x32ffa),('030',0x32ffa),('020',0x33fff)]:
    pair=[]
    for label,selected in [('off',mask),('on',mask|0x80000)]:
        out=root/f'completion-e2-complete-{machine}-{label}'
        if out.exists():raise SystemExit(f'Refusing overwrite: {out}')
        print('START',machine,label,flush=True)
        log=root/f'completion-e2-complete-{machine}-{label}.driver.log'
        with log.open('w') as stream:
            subprocess.run([sys.executable,'-B','tools/completion_e2_case.py',machine,hex(selected),str(out)],stdout=stream,stderr=subprocess.STDOUT,check=True)
        result=json.loads((out/'opening.json').read_text())
        pair.append(result)
        print('CASE',machine,label,result['fps'],flush=True)
    assert pair[0]['slave_sha256']==pair[1]['slave_sha256']
    print('PAIR',machine,100*(pair[1]['fps']/pair[0]['fps']-1),flush=True)
print('FEATURE MATRIX COMPLETE',flush=True)
