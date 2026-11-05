from pathlib import Path
import os,subprocess,json,hashlib,sys
repo=Path(__file__).resolve().parents[3];r=repo/'tmp/dev';stage=int(sys.argv[1]);tag=f'b6-s{stage}'
for kind in ('state','elapsed','replay'):assert json.loads((r/f'manifest/step5-{tag}-{kind}-validation.json').read_text())['status']=='passed'
files=['Games/FerrariFormulaOne_NativeExact.s']
settings={'user.name':'Vesa Halttunen','user.email':'vesuri@jormas.com','user.signingkey':'','core.hooksPath':'/dev/null','commit.gpgsign':'false','tag.gpgsign':'false','push.gpgSign':'false'}
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_') and k!='EMAIL'};env.update(GIT_AUTHOR_NAME='Vesa Halttunen',GIT_AUTHOR_EMAIL='vesuri@jormas.com',GIT_COMMITTER_NAME='Vesa Halttunen',GIT_COMMITTER_EMAIL='vesuri@jormas.com',GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1')
base=['git']
for k,v in settings.items():base+=['-c',k+'='+v]
def git(*args):return subprocess.check_output(base+list(args),cwd=repo,env=env,text=True).strip()
assert git('branch','--show-current')=='ferrariformulaone'
for which in ('GIT_AUTHOR_IDENT','GIT_COMMITTER_IDENT'):assert git('var',which).startswith('Vesa Halttunen <vesuri@jormas.com> ')
for k,v in settings.items():assert git('config','--get',k)==v
assert git('diff','--cached','--name-only')==''
assert set(git('diff','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines())==set(files)
git('diff','--check');git('config','--local','core.hooksPath','/dev/null')
profiles={}
for p in ('a1200-fast','a1200'):
 d=r/f'tmp/step5/{p}-{tag}-profile';x=json.loads((d/'profile.json').read_text());c=x['per_update_cycles'];assert len(c)==20
 assert c==json.loads((d/'percar.json').read_text())['per_update_totals']==json.loads((d/'classified.json').read_text())['per_update_totals']
 profiles[p]=dict(mean=x['mean_cycles'],peak=max(c),worst_five=max(sum(c[i:i+5])/5 for i in range(16)))
assert profiles['a1200-fast']['mean']<=165000
names={1:'Inline Ferrari divisions with dead condition codes',2:'Inline additional Ferrari native multiplies',3:'Integrate Ferrari register lookahead loop',4:'Use direct Ferrari sine and cosine table helpers',5:'Preserve native multiply flags with hardware arithmetic'}
git('add','--',*files);print(git('commit','--no-gpg-sign','-m',names[stage],'-m',f'Default-off B6 substep {stage}. Both 020 profiles pass 101-checkpoint exact-state, elapsed and arithmetic replay checks. Fast matched mean {profiles["a1200-fast"]["mean"]} cycles, peak {profiles["a1200-fast"]["peak"]}. Ordinary slave unchanged.'))
sha=git('rev-parse','HEAD');assert git('show','-s','--format=%an%n%ae%n%cn%n%ce%n%G?',sha).splitlines()==['Vesa Halttunen','vesuri@jormas.com','Vesa Halttunen','vesuri@jormas.com','N'];assert git('status','--porcelain')==''
report=dict(status='passed',scope=f'B6 substep {stage}; final B6 gate pending until all substeps',commit=sha,profiles=profiles,source_hashes={f:hashlib.sha256((repo/f).read_bytes()).hexdigest() for f in files})
(r/f'manifest/step5-{tag}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
p=r/'docs/STEP5_CAPACITY.md';p.write_text(p.read_text()+f'\n### B6 substep {stage}\n\nDefault-off candidate committed as `{sha}`. Matched twenty complete lean updates from loop 125 (installation excluded; only unsuccessful pacing polls removed). Both profiles pass the unchanged 101-checkpoint exact-state inventory, player fractional state, elapsed and full replay oracles.\n\n'+ '\n'.join(f'- {k}: mean {v["mean"]}, worst rolling five {v["worst_five"]}, peak {v["peak"]} cycles.' for k,v in profiles.items())+f'\n\nEvidence: `manifest/step5-{tag}-validation.json`, linked state/elapsed/replay reports and `tmp/step5/*-{tag}-profile`. Further B6 work and final pulse/debt gate remain pending.\n')
p=r/'manifest/project.json';d=json.loads(p.read_text());d[f'step5_{tag}_validation']=f'tmp/dev/manifest/step5-{tag}-validation.json';d['step5_b6_status']=f'Substep {stage} passed; full B6 remains in progress.';p.write_text(json.dumps(d,indent=2)+'\n');print(sha,profiles)
