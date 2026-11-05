from pathlib import Path
import os,sys,subprocess,json
r=Path(__file__).resolve().parents[1];repo=r.parents[1];os.chdir(repo)
name=sys.argv[1];env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_CONFIG','GIT_AUTHOR','GIT_COMMITTER')) and k!='EMAIL'}
env.update(GIT_AUTHOR_NAME='Vesa Halttunen',GIT_AUTHOR_EMAIL='vesuri@jormas.com',GIT_COMMITTER_NAME='Vesa Halttunen',GIT_COMMITTER_EMAIL='vesuri@jormas.com')
git=['git','-c','user.name=Vesa Halttunen','-c','user.email=vesuri@jormas.com','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','-c','tag.gpgsign=false','-c','user.signingkey=']
def run(*args):return subprocess.check_output(git+list(args),env=env,text=True).strip()
assert run('branch','--show-current')=='ferrariformulaone'
assert not run('diff','--cached','--name-only')
for field in ['GIT_AUTHOR_IDENT','GIT_COMMITTER_IDENT']:
 v=run('var',field);assert v.startswith('Vesa Halttunen <vesuri@jormas.com>');print(field,v)
for k,v in [('core.hooksPath','/dev/null'),('commit.gpgsign','false'),('tag.gpgsign','false')]:assert run('config','--get',k)==v
assert not run('diff','--check')
manifest=r/f'manifest/step5-c4-{name}-validation.json';j=json.loads(manifest.read_text());assert j['status']=='passed'
files=['Games/'+x for x in j['source_sha256']]
run('add','--',*files);assert set(run('diff','--cached','--name-only').splitlines())==set(files)
print(run('commit','--no-gpg-sign','-F',str(r/f'tmp/step5/{name}-commit-message.txt')))
sha=run('rev-parse','HEAD');raw=run('cat-file','commit',sha);assert '\ngpgsig ' not in raw
for role in ['author','committer']:assert role+' Vesa Halttunen <vesuri@jormas.com>' in raw
j['commit']=sha;manifest.write_text(json.dumps(j,indent=2)+'\n')
for path in ['project.json','step5-c4-open-cases.json']:
 p=r/'manifest'/path;j=json.loads(p.read_text())
 if path=='project.json':j[f'step5_c4_{name}_commit']=sha
 else:
  case=next((x for x in j['cases'] if x['id']=='C4-'+name.upper()),None)
  if case is not None:case['resolution']['commit']=sha
 p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'docs/STEP5_CAPACITY.md';p.write_text(p.read_text()+f'\n{name.upper()} findings committed as `{sha}`.\n');print(sha)
