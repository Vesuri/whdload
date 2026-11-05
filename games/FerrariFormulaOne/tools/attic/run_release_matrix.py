from pathlib import Path
import os,sys,subprocess,json,time
r=Path(__file__).resolve().parents[1];group=sys.argv[1];results=[]
if group=='laps':
 for preparatory in ('memory-followup','states-accepted'):
  subprocess.run([sys.executable,str(__file__),preparatory],check=True)
 subprocess.run([sys.executable,str(r/'tools/run_release_baselines.py')],check=True)
if group=='accelerated':
 cases=[('census',p,{'C1_VARIANT':'clock-v2-'+n}) for p in ('030-50','040-25','040-40','060-50') for n in ('a','b')]
 cases += [('timing',p,{'C1_VARIANT':'clock-v2'}) for p in ('030-50','040-25','040-40','060-50')]
elif group=='memory-followup':
 old=str(r/'tmp/runtime-17/WHDLoad_17.0_usr/WHDLoad/C/WHDLoad');v20=str(r/'tmp/runtime-20/WHDLoad_20.0_usr/WHDLoad/C/WHDLoad')
 cases=[('smoke','a1200',{'C1_VARIANT':tag,'WHDLOAD_BINARY':runtime,'RELEASE_WHD_ARGS':'CUSTOM1=1 CUSTOM2=1 '+option,'RELEASE_RUN_SCRIPT':'amiga/run-release-stdio.sh'}) for tag,runtime,option in [('current-expchip',os.environ['WHDLOAD_BINARY'],'ExpChip'),('runtime17-expchip',old,'ExpChip'),('runtime20',v20,''),('runtime20-expchip',v20,'ExpChip')]]
 cases += [('smoke','a1200',{'C1_VARIANT':'observer-control','RELEASE_FSUAE':str(r/'tmp/step3/fs-uae-q03-final'),'RELEASE_RUN_SCRIPT':'amiga/run-release-stdio.sh'})]
elif group=='diagnostics':
 old=str(r/'tmp/runtime-17/WHDLoad_17.0_usr/WHDLoad/C/WHDLoad')
 cases=[('smoke',p,{'C1_VARIANT':'runtime17-requester','WHDLOAD_BINARY':old,'RELEASE_RUN_SCRIPT':'amiga/run-release-diagnostic.sh'}) for p in ('a500','a1200','a500-fast')]
 cases += [('smoke','a500',{'C1_VARIANT':'slow-1024-requester','RELEASE_PROFILE_OVERRIDES':json.dumps({'SLOW_KB':'1024'}),'RELEASE_RUN_SCRIPT':'amiga/run-release-diagnostic.sh'})]
elif group=='runtime-memory':
 old=str(r/'tmp/runtime-17/WHDLoad_17.0_usr/WHDLoad/C/WHDLoad')
 cases=[('smoke',p,{'C1_VARIANT':'runtime17','WHDLOAD_BINARY':old}) for p in ('a500','a1200','a1200-fast','060-50')]
 cases += [('smoke','a500',{'C1_VARIANT':'slow-'+str(n),'RELEASE_PROFILE_OVERRIDES':json.dumps({'SLOW_KB':str(n)})}) for n in (512,1024,1536)]
 cases += [('smoke','a500-fast',{'C1_VARIANT':'fast-only-2m','RELEASE_PROFILE_OVERRIDES':json.dumps({'SLOW_KB':'0'})}),('smoke','a1200',{'C1_VARIANT':'chip-1m','RELEASE_PROFILE_OVERRIDES':json.dumps({'CHIP_KB':'1024'})})]
elif group=='cache-mmu':
 cases=[('census',p,{'C1_VARIANT':'cache-'+flag.lower(),'RELEASE_WHD_ARGS':'CUSTOM1=1 CUSTOM2=1 '+flag}) for p,flag in [('030-50','NoCache'),('030-50','DCache'),('040-25','DCache'),('060-50','DCache'),('060-50','BranchCache')]]
 cases += [('smoke',p,{'C1_VARIANT':'mmu','RELEASE_FSUAE':os.environ['FSUAE_MMU'],'RELEASE_PROFILE_OVERRIDES':json.dumps({'CPU':cpu})}) for p,cpu in [('040-25','68040'),('060-50','68060')]]
elif group=='laps':cases=[('lap',p,{}) for p in ('a500','a1200','a1200-fast')]
elif group in ('states','states-accepted'):
 cases=[('state',p,{'C1_VARIANT':'normal-8m','RELEASE_PROFILE_OVERRIDES':json.dumps({'FAST_KB':'8192'})} if p=='a1200-fast' else {'C1_VARIANT':'normal'}) for p in ('a1200-fast','030-50','040-25','040-40','060-50')]
 cases += [('state',p,{'C1_VARIANT':flag.lower(),'RELEASE_WHD_ARGS':'CUSTOM1=1 CUSTOM2=1 '+flag}) for p,flag in [('030-50','NoCache'),('030-50','DCache'),('040-25','DCache'),('060-50','DCache'),('060-50','BranchCache')]]
elif group in ('frames','frames-accepted'):
 cases=[('frame',p,{'C1_VARIANT':'normal-8m','RELEASE_PROFILE_OVERRIDES':json.dumps({'FAST_KB':'8192'})} if p=='a1200-fast' else {'C1_VARIANT':'normal'}) for p in ('a1200-fast','030-50','040-25','040-40','060-50')]
 cases += [('frame',p,{'C1_VARIANT':flag.lower(),'RELEASE_WHD_ARGS':'CUSTOM1=1 CUSTOM2=1 '+flag}) for p,flag in [('030-50','NoCache'),('030-50','DCache'),('040-25','DCache'),('060-50','DCache'),('060-50','BranchCache')]]
elif group=='legacy':cases=[('default_c1','',{'RELEASE_CUSTOM1':str(c),'C1_VARIANT':'custom1-'+str(c)}) for c in (0,1)]
else:raise SystemExit(group)
if group=='states-accepted':cases=[x for x in cases if x[1] in ('030-50','040-25') and x[2]['C1_VARIANT']=='normal']
if group=='states-accepted':
 old=str(r/'tmp/runtime-17/WHDLoad_17.0_usr/WHDLoad/C/WHDLoad')
 cases=[('smoke',profile,{'C1_VARIANT':tag,'WHDLOAD_BINARY':runtime,'RELEASE_WHD_ARGS':'CUSTOM1=1 CUSTOM2=1 ConfigDelay=0','RELEASE_RUN_SCRIPT':'amiga/run-release-stdio.sh'}) for profile,tag,runtime in [('a1200','current-configdelay0',os.environ['WHDLOAD_BINARY']),('a500','runtime17-configdelay0',old),('a1200','runtime17-configdelay0',old)]]+cases
if group.endswith('-accepted'):
 for _,_,extra in cases:extra['ARM']='accepted'
for kind,profile,extra in cases:
 variant=extra.get('C1_VARIANT','candidate');name='c4-q03-release-'+(kind+'-'+extra.get('ARM','production') if kind in ('state','frame') else kind)+'-'+profile+'-'+variant
 evidence=r/'tmp/step5'/name/'result.json'
 if evidence.exists() and json.loads(evidence.read_text()).get('status') in ('passed','captured'):
  print('Already passed',name,flush=True);continue
 script='capture_release_census.py' if kind=='census' else 'capture_release_states.py' if kind=='state' else 'capture_release_frames.py' if kind=='frame' else 'test_release_'+kind+'.py'
 env=dict(os.environ);env.update(extra);log=r/'tmp/step5'/('release-matrix-'+group+'-'+(profile or 'all')+'-'+variant+'.log')
 print('RUN',name,flush=True);start=time.time()
 with log.open('w') as f:
  result=subprocess.run([sys.executable,str(r/'tools'/script)]+([profile] if profile else []),env=env,stdout=f,stderr=subprocess.STDOUT)
 results.append(dict(name=name,returncode=result.returncode,seconds=time.time()-start,log=str(log.relative_to(r)),evidence=str(evidence.relative_to(r))))
 (r/'manifest'/('release-'+group+'-runs.json')).write_text(json.dumps(results,indent=2)+'\n')
 print('DONE',name,result.returncode,flush=True)
