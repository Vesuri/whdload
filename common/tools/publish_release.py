"""Publish a game's release archive on GitHub (docs/releasing.md, "Publishing").

    make release [PUBLISH=1] [REPLACE=1]     (common/release.sh runs make dist, then this)

From the release slave's $VER (version, date) and game.conf (TITLE, AUTHOR, via the
environment) it derives:
  tag      <Game>Enhanced-<version>-<YYYYMMDD>, the archive's name without .lha, a
           lightweight tag on HEAD, the commit the archive was just built from
  title    <TITLE> Enhanced <version> (dd.mm.yyyy)
  notes    the change points of that version's history entry in the archive's ReadMe,
           without the WHDLoad requirement line
Without PUBLISH=1 it only prints them. With it, it checks the identity, the GitHub account
and that HEAD is pushed, then tags, creates the release, uploads the archive and its
.sha256, downloads the archive again to compare, and lists the release in the root
README.md's games table (a commit of README.md alone, pushed). NOTES=<file> gives the notes
when the ReadMe's entry is not a list of "- " change points. REPLACE=1 first deletes the
game's earlier releases and their tags (any tag starting with <Game>Enhanced-); without it
an existing release of the game stops the run. GitHub's API fails intermittently, so every
remote step is retried and checked by reading the state back.
"""
import argparse
import datetime
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_release import date_of, version_of  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OWNER = 'Vesuri'
GH_REPO = f'{OWNER}/whdload'
EMAIL = 'vesuri@jormas.com'
RELEASES = f'https://github.com/{GH_REPO}/releases/tag/'
LHA = os.environ.get('LHA') or 'lha'


def run(*cmd, check=True, cwd=REPO):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f'{" ".join(cmd)} failed:\n{r.stdout}{r.stderr}')
    return r


def retry(step, done, what, tries=5):
    """Run step until done() holds; GitHub sometimes fails a request it then performs."""
    for attempt in range(tries):
        if done():
            return
        step()
        if done():
            return
        time.sleep(2 * (attempt + 1))
    sys.exit(f'{what} failed after {tries} attempts')


# --- what the release is -------------------------------------------------------------------

VERSION_LINE = r'^\s*version\s+v?{}\s*\('
REQUIREMENT = re.compile(r'\brequire[sd]?\b.*\bwhdload\b|\bwhdload\b.*\brequired\b', re.I)


def readme_of(archive):
    """The archive's ReadMe (the member named readme in any case), as text."""
    with tempfile.TemporaryDirectory(dir=REPO / 'tmp') as d:
        run(LHA, f'xqw={d}', str(archive.resolve()))
        readmes = [p for p in Path(d).rglob('*') if p.is_file() and p.name.lower() == 'readme']
        if len(readmes) != 1:
            sys.exit(f'{archive.name}: expected one ReadMe, found '
                     f'{[str(p.relative_to(d)) for p in readmes] or "none"}')
        data = readmes[0].read_bytes()
    return data.decode('latin-1').replace('\r\n', '\n').replace('\r', '\n')


def notes_of(readme, version):
    """The change points of the version's history entry, as Markdown list items."""
    lines = readme.split('\n')
    head = re.compile(VERSION_LINE.format(re.escape(version)), re.I)
    start = next((i for i, line in enumerate(lines) if head.match(line)), None)
    if start is None:
        sys.exit(f'the ReadMe has no history entry "version {version} (...)"; '
                 'give the notes with NOTES=<file>')
    items = []
    for line in lines[start + 1:]:
        if not line.strip() or head.match(line) or re.match(r'^\s*version\s', line, re.I):
            break
        text = line.strip()
        if text.startswith('- '):
            items.append([text[2:].strip()])
        elif items:
            items[-1].append(text)
        else:
            sys.exit(f'unexpected line in the version {version} entry: {line!r}; '
                 'give the notes with NOTES=<file>')
    items = [i for i in items if not REQUIREMENT.search(' '.join(i))]
    if not items:
        sys.exit(f'the version {version} entry lists no changes')
    out = []
    for item in items:
        out.append(f'- {item[0]}')
        out += [f'  {t}' for t in item[1:]]
    return '\n'.join(out) + '\n'


# --- checks before publishing --------------------------------------------------------------

def check_identity():
    for var in ('GIT_AUTHOR_IDENT', 'GIT_COMMITTER_IDENT'):
        ident = run('git', 'var', var).stdout
        if f'<{EMAIL}>' not in ident or not ident.startswith('Vesa Halttunen '):
            sys.exit(f'{var} is {ident.split(">")[0]}>, not Vesa Halttunen <{EMAIL}>')
    if run('git', 'config', '--get', 'commit.gpgsign', check=False).stdout.strip() == 'true':
        sys.exit('commit.gpgsign is on')
    if run('git', 'config', '--get', 'core.hooksPath', check=False).stdout.strip() != '/dev/null':
        sys.exit('core.hooksPath is not /dev/null')
    login = run('gh', 'api', 'user', '--jq', '.login').stdout.strip()
    if login != OWNER:
        sys.exit(f'the active GitHub account is {login}, not {OWNER} (gh auth switch)')


def check_pushed(head):
    status = gh_api(f'compare/{head}...main', '.status')
    if status not in ('identical', 'ahead'):
        sys.exit(f'HEAD {head[:8]} is not on main on GitHub ({status or "unknown"}); push it first')


# --- GitHub --------------------------------------------------------------------------------
# Lookups go through the GitHub API (HTTPS); only pushing a tag or commit uses git.

def gh_api(path, jq, tries=5):
    """The jq result for repos/<repo>/<path>, or None when GitHub answers 404."""
    for attempt in range(tries):
        r = run('gh', 'api', f'repos/{GH_REPO}/{path}', '--jq', jq, check=False)
        if r.returncode == 0:
            return r.stdout.strip()
        if 'HTTP 404' in r.stderr:
            return None
        time.sleep(2 * (attempt + 1))
    sys.exit(f'GitHub API {path} failed:\n{r.stderr}')


def remote_tag(tag):
    """The commit the tag names on GitHub (lightweight tags only), or None."""
    return gh_api(f'git/ref/tags/{tag}', '.object.sha') or None


def release_exists(tag):
    return run('gh', 'release', 'view', tag, '-R', GH_REPO, check=False).returncode == 0


def asset_count(tag):
    r = run('gh', 'release', 'view', tag, '-R', GH_REPO, '--json', 'assets',
            '--jq', '.assets|length', check=False)
    return int(r.stdout.strip() or 0) if r.returncode == 0 else 0


def game_releases(game):
    r = run('gh', 'release', 'list', '-R', GH_REPO, '--limit', '200',
            '--json', 'tagName', '--jq', '.[].tagName')
    tags = set(r.stdout.split())
    refs = gh_api(f'git/matching-refs/tags/{game}Enhanced-', '.[].ref') or ''
    tags |= {ref[len('refs/tags/'):] for ref in refs.split()}
    return sorted(t for t in tags if t.startswith(f'{game}Enhanced-'))


def delete_release(tag):
    retry(lambda: run('gh', 'release', 'delete', tag, '-R', GH_REPO, '--cleanup-tag', '-y',
                      check=False),
          lambda: not release_exists(tag), f'deleting release {tag}')
    retry(lambda: run('git', 'push', '-q', 'origin', f':refs/tags/{tag}', check=False),
          lambda: remote_tag(tag) is None, f'deleting tag {tag}')
    run('git', 'tag', '-d', tag, check=False)


def publish(tag, head, title, notes, archive, digest):
    run('git', 'tag', tag, head)
    retry(lambda: run('git', 'push', '-q', 'origin', f'refs/tags/{tag}', check=False),
          lambda: remote_tag(tag) == head, f'pushing tag {tag}')
    with tempfile.NamedTemporaryFile('w', suffix='.md', dir=REPO / 'tmp', delete=False) as f:
        f.write(notes)
    try:
        retry(lambda: run('gh', 'release', 'create', tag, '-R', GH_REPO, '--verify-tag',
                          '--title', title, '--notes-file', f.name, check=False),
              lambda: release_exists(tag), f'creating release {tag}')
    finally:
        os.unlink(f.name)
    retry(lambda: run('gh', 'release', 'upload', tag, '-R', GH_REPO, '--clobber',
                      str(archive), str(digest), check=False),
          lambda: asset_count(tag) == 2, f'uploading to {tag}')
    with tempfile.TemporaryDirectory(dir=REPO / 'tmp') as d:
        retry(lambda: run('gh', 'release', 'download', tag, '-R', GH_REPO, '-p', archive.name,
                          '-D', d, '--clobber', check=False),
              lambda: (Path(d) / archive.name).is_file(), f'downloading {archive.name}')
        got = hashlib.sha256((Path(d) / archive.name).read_bytes()).hexdigest()
    if got != digest.read_text().split()[0]:
        sys.exit(f'the published {archive.name} differs from {digest.name}')


# --- README --------------------------------------------------------------------------------

def readme_row(text, title, author, label, tag):
    """The root README.md with the game's row linking the release."""
    lines = text.split('\n')
    i = lines.index('|---|---|---|') + 1
    j = i
    while j < len(lines) and lines[j].startswith('|'):
        j += 1
    name = f'{title} Enhanced'
    rows = [r for r in lines[i:j] if r.split('|')[1].strip() != name]
    old = [r for r in lines[i:j] if r.split('|')[1].strip() == name]
    if old:
        author = old[0].split('|')[2].strip()
    rows.append(f'| {name} | {author} | [{label}]({RELEASES}{tag}) |')
    rows.sort(key=lambda r: r.split('|')[1].strip().lower())
    lines[i:j] = rows
    return '\n'.join(lines)


def list_in_readme(title, author, label, tag):
    path = REPO / 'README.md'
    before = path.read_text()
    after = readme_row(before, title, author, label, tag)
    if after == before:
        return False
    if run('git', 'status', '--porcelain', '--', 'README.md').stdout.strip():
        sys.exit('README.md has uncommitted changes; list the release by hand')
    path.write_text(after)
    run('git', 'commit', '-q', '--only', '-m', f'List the {title} Enhanced {label} release',
        '--', 'README.md')
    # A successful push moves origin/main to HEAD.
    retry(lambda: run('git', 'push', '-q', 'origin', 'main', check=False),
          lambda: run('git', 'rev-list', '--count', 'origin/main..HEAD').stdout.strip() == '0',
          'pushing README.md')
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--game', required=True)
    ap.add_argument('--slave', type=Path, required=True)
    ap.add_argument('--dist', type=Path, required=True)
    args = ap.parse_args()
    title, author = os.environ['TITLE'], os.environ.get('AUTHOR', '')
    publish_now = os.environ.get('PUBLISH') == '1'
    replace = os.environ.get('REPLACE') == '1'

    version, stamp = version_of(args.slave), date_of(args.slave)
    date = datetime.date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:]))
    label = f'{version} ({date:%d.%m.%Y})'
    tag = f'{args.game}Enhanced-{version}-{stamp}'
    archive = args.dist / f'{tag}.lha'
    digest = args.dist / f'{tag}.lha.sha256'
    for p in (archive, digest):
        if not p.is_file():
            sys.exit(f'make dist did not write {p}')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != digest.read_text().split()[0]:
        sys.exit(f'{archive.name} does not match {digest.name}')
    if os.environ.get('NOTES'):
        notes = Path(os.environ.get('CALLER_DIR') or os.getcwd(), os.environ['NOTES']).read_text()
    else:
        notes = notes_of(readme_of(archive), version)
    head = run('git', 'rev-parse', 'HEAD').stdout.strip()
    release_title = f'{title} Enhanced {label}'
    existing = game_releases(args.game)

    print(f'tag      {tag} on {head[:8]} ({run("git", "log", "-1", "--format=%s").stdout.strip()})')
    print(f'title    {release_title}')
    print(f'files    {archive.name}, {digest.name}')
    if existing:
        print(f'existing {", ".join(existing)}' + (' (deleted first: REPLACE=1)' if replace else ''))
    print('notes')
    print(''.join(f'         {line}\n' for line in notes.splitlines()), end='')
    if existing and not replace:
        sys.exit(f'{args.game} already has {", ".join(existing)}; REPLACE=1 deletes '
                 'and republishes')
    if not publish_now:
        print('dry run: make release PUBLISH=1 publishes this')
        return

    check_identity()
    check_pushed(head)
    for old in existing:
        delete_release(old)
        print(f'deleted  {old}')
    publish(tag, head, release_title, notes, archive, digest)
    print(f'released {RELEASES}{tag}')
    if list_in_readme(title, author, label, tag):
        print(f'README   listed, {run("git", "rev-parse", "--short", "HEAD").stdout.strip()}')


if __name__ == '__main__':
    main()
