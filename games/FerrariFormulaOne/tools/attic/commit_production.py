from pathlib import Path
import os,sys,subprocess,json
r=Path(__file__).resolve().parents[1];repo=r.parents[1];os.chdir(repo)
env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_CONFIG','GIT_AUTHOR','GIT_COMMITTER')) and k!='EMAIL'}
env.update(GIT_AUTHOR_NAME='Vesa Halttunen',GIT_AUTHOR_EMAIL='vesuri@jormas.com',GIT_COMMITTER_NAME='Vesa Halttunen',GIT_COMMITTER_EMAIL='vesuri@jormas.com')
git=['git','-c','user.name=Vesa Halttunen','-c','user.email=vesuri@jormas.com','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','-c','tag.gpgsign=false','-c','user.signingkey=']
def run(*args):return subprocess.check_output(git+list(args),env=env,text=True).strip()
assert run('branch','--show-current')=='ferrariformulaone'
assert not run('diff','--cached','--name-only')
for field in ['GIT_AUTHOR_IDENT','GIT_COMMITTER_IDENT']:
 v=run('var',field);assert v.startswith('Vesa Halttunen <vesuri@jormas.com>');print(field,v)
for k,v in [('core.hooksPath','/dev/null'),('commit.gpgsign','false'),('tag.gpgsign','false')]:assert run('config','--get',k)==v
assert not run('diff','--check')
files=[x for x in run('diff','--name-only').splitlines() if x.startswith('Games/FerrariFormulaOne')]
files += [x for x in run('ls-files','--others','--exclude-standard','Games/FerrariFormulaOne').splitlines()]
assert files
run('add','--',*files);assert set(run('diff','--cached','--name-only').splitlines())==set(files)
print(run('commit','--no-gpg-sign','-m',sys.argv[1]))
sha=run('rev-parse','HEAD');raw=run('cat-file','commit',sha);assert '\ngpgsig ' not in raw
for role in ['author','committer']:assert role+' Vesa Halttunen <vesuri@jormas.com>' in raw
p=r/'manifest/production-integration.json';j=json.loads(p.read_text());j.setdefault('commits',[]).append(sha);p.write_text(json.dumps(j,indent=2)+'\n');print(sha)
