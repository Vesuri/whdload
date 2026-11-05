"""Commit a fully accepted cohesive source stage with the personal repository rules."""
from pathlib import Path
import sys,os,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];root=r.parent.parent;os.chdir(root)
stage,slug=sys.argv[1:];mp=r/f'manifest/step5-c4-{slug}-validation.json';m=json.loads(mp.read_text());assert m['status']=='passed'
for name,digest in m['source_sha256'].items():assert hashlib.sha256((root/'Games'/name).read_bytes()).hexdigest()==digest,name
env=os.environ.copy()
for key in list(env):
 if key.startswith(('GIT_CONFIG','GIT_AUTHOR','GIT_COMMITTER')) or key=='EMAIL':del env[key]
env.update(GIT_AUTHOR_NAME='Vesa Halttunen',GIT_AUTHOR_EMAIL='vesuri@jormas.com',GIT_COMMITTER_NAME='Vesa Halttunen',GIT_COMMITTER_EMAIL='vesuri@jormas.com')
git=['git','-c','user.name=Vesa Halttunen','-c','user.email=vesuri@jormas.com','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','-c','tag.gpgsign=false','-c','user.signingkey=']
def run(*args):return subprocess.check_output(git+list(args),env=env,text=True).strip()
assert run('branch','--show-current')=='ferrariformulaone'
assert not run('diff','--cached','--name-only'),'Do not mix already-staged work into this commit'
for name in ('GIT_AUTHOR_IDENT','GIT_COMMITTER_IDENT'):
 value=run('var',name);assert value.startswith('Vesa Halttunen <vesuri@jormas.com>');print(name,value)
for k,v in [('core.hooksPath','/dev/null'),('commit.gpgsign','false'),('tag.gpgsign','false')]:assert run('config','--get',k)==v
assert not run('diff','--check')
files=['Games/'+n for n in m['source_sha256']];run('add','--',*files);assert set(run('diff','--cached','--name-only').splitlines())==set(files)
print(run('commit','--no-gpg-sign','-F',str(r/f'tmp/step5/{stage}-commit-message.txt')))
sha=run('rev-parse','HEAD');raw=run('cat-file','commit',sha);assert '\ngpgsig ' not in raw
for identity in ('author','committer'):assert f'{identity} Vesa Halttunen <vesuri@jormas.com>' in raw
m['commit']=sha;mp.write_text(json.dumps(m,indent=2)+'\n')
p=r/'manifest/project.json';j=json.loads(p.read_text());j[f'step5_c4_{stage}_commit']=sha;p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'manifest/step5-c4-open-cases.json';j=json.loads(p.read_text());j['latest_accepted_performance_change']['commit']=sha;p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'docs/STEP5_CAPACITY.md';p.write_text(p.read_text()+f'\n{stage.upper()} source and measured findings committed as `{sha}`.\n');print(sha)
