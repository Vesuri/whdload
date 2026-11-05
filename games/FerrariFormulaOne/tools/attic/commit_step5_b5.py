from pathlib import Path
import os,subprocess,json,hashlib
repo=Path(__file__).resolve().parents[3]
report=json.loads((repo/'tmp/dev/manifest/step5-b5-validation.json').read_text());assert report['status']=='passed'
files=sorted(report['source_hashes'])
assert files==sorted('Games/FerrariFormulaOne_'+n+'.s' for n in ('Sqrt','Speed','Velocity','Wear','UpdateHooks'))
for f,sha in report['source_hashes'].items():assert hashlib.sha256((repo/f).read_bytes()).hexdigest()==sha
settings={'user.name':'Vesa Halttunen','user.email':'vesuri@jormas.com','user.signingkey':'','core.hooksPath':'/dev/null','commit.gpgsign':'false','tag.gpgsign':'false','push.gpgSign':'false'}
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_') and k!='EMAIL'}
env.update(GIT_AUTHOR_NAME='Vesa Halttunen',GIT_AUTHOR_EMAIL='vesuri@jormas.com',GIT_COMMITTER_NAME='Vesa Halttunen',GIT_COMMITTER_EMAIL='vesuri@jormas.com',GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1')
assert {k for k in env if k.startswith('GIT_')}=={'GIT_AUTHOR_NAME','GIT_AUTHOR_EMAIL','GIT_COMMITTER_NAME','GIT_COMMITTER_EMAIL','GIT_CONFIG_GLOBAL','GIT_CONFIG_NOSYSTEM'}
base=['git']
for k,v in settings.items():base+=['-c',k+'='+v]
def git(*args):return subprocess.check_output(base+list(args),cwd=repo,env=env,text=True).strip()
assert git('branch','--show-current')=='ferrariformulaone';assert Path(git('rev-parse','--show-toplevel'))==repo
for which in ('GIT_AUTHOR_IDENT','GIT_COMMITTER_IDENT'):assert git('var',which).startswith('Vesa Halttunen <vesuri@jormas.com> ')
for k,v in settings.items():assert git('config','--get',k)==v
assert git('diff','--cached','--name-only')=='';assert sorted(git('diff','--name-only').splitlines())==files
git('diff','--check');git('config','--local','core.hooksPath','/dev/null')
print('Verified personal author/committer, unsigned commits/tags/pushes, disabled hooks and sanitized Git environment.')
git('add','--',*files)
print(git('commit','--no-gpg-sign','-m','Tune Ferrari 020 conversion helpers','-m','Add default-off exact seed/Newton roots and streamline scalar, velocity and wear helpers. Preserve arithmetic failure, carry and register contracts; configure VERIFY scalar capacity consistently for chip-only captures.\n\nMatched Fast player conversion helpers fall from 6998.35 to 4968 cycles. Guest arithmetic, exact-state, elapsed/replay and direct-hook ABI checks pass. Disabled binaries remain byte-identical to B4.'))
sha=git('rev-parse','HEAD');identity=git('show','-s','--format=%an%n%ae%n%cn%n%ce%n%G?',sha).splitlines()
assert identity==['Vesa Halttunen','vesuri@jormas.com','Vesa Halttunen','vesuri@jormas.com','N'];assert git('status','--porcelain')==''
report['commit']=sha;(repo/'tmp/dev/manifest/step5-b5-validation.json').write_text(json.dumps(report,indent=2)+'\n')
p=repo/'tmp/dev/manifest/project.json';d=json.loads(p.read_text());d['step5_b5_commit']=sha;p.write_text(json.dumps(d,indent=2)+'\n')
p=repo/'tmp/dev/docs/STEP5_CAPACITY.md';s=p.read_text();s+='\nB5 implementation commit: `'+sha+'` (personal identity; unsigned; hooks disabled).\n';p.write_text(s)
print('Committed',sha,'and verified clean tracked tree.')
