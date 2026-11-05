import os,sys,subprocess,json
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');rows=[]
checks=[(c,c,'check_a.py',False,{},['--normal']) for c in ['a500-1m','a1200','a1200-fast','030-50','040-25','060-50']]
checks += [('000-fast','a500-1m','check_a.py',False,{'FAST_KB':'8192'},['--normal']),('off-020','a1200-fast','check_a.py',False,{'WHD_ARGS':'CUSTOM2=0'},['--normal']),('off-040','040-25','check_a.py',False,{'WHD_ARGS':'CUSTOM2=0'},['--normal'])]
checks += [(c,c,'cache_mmu_policy_c.py',True,{'WHD_ARGS':'MMU CUSTOM2=1','EXTRA_ARGS':'--uae_cpu_data_cache=true --uae_uaeboard=full'},[]) for c in ['040-mmu','060-mmu']]
checks += [('keyboard','040-25','input_b.py',False,{'RR_STACK_TEST':'1'},[]),('cd32','040-25','input_b.py',False,{'RR_STACK_TEST':'1','RR_PAD':'1'},[]),('exposure','040-25','npc_acceleration_trace_c.py',False,{},[])]
for i,(name,cell,script,diag,extra,args) in enumerate(checks):
 env=config(cell);env.update(SLAVE=str(root/'tmp/g-release-build'/('RoadRash-verify.slave' if diag else 'RoadRash.slave')),DEBUG_PORT=str(28100+i));env['WHD_ARGS']+=' CUSTOM2=1';env.update(extra)
 out=root/f'tmp/g-check-{name}';out.mkdir()
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/'+script,str(out)]+args,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
 finally:cleanup(out)
 row=dict(name=name,returncode=p.returncode)
 if script=='check_a.py' and p.returncode==0:row['fps']=json.loads((out/'result.json').read_text())['fps']
 rows.append(row);(root/'tmp/g-checks.json').write_text(json.dumps(rows,indent=2));print(row,flush=True)
 assert not p.returncode
