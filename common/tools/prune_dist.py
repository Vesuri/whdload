"""Remove older release archives from dist/, keeping the latest of each (docs/releasing.md).

    make prune-dist [DRY=1]

Archives are <Name>-<version>[-<YYYYMMDD>].lha with a .sha256 beside each. Archives with
the same <Name> are versions of one release; the latest is the highest version, then the
latest date, and a final version (2.0) is later than its betas (2.0b). The others and
their .sha256 are deleted; with DRY=1 they are only listed. Other files are left alone.
"""
import os
import re
import sys

ARCHIVE = re.compile(r"^(?P<name>.+?)-(?P<version>\d+(?:\.\d+)*[a-z]*)(?:-(?P<date>\d{8}))?\.lha$")
VERSION = re.compile(r"^(?P<numbers>\d+(?:\.\d+)*)(?P<suffix>[a-z]*)$")


def order(match):
    version = VERSION.match(match["version"])
    numbers = tuple(int(n) for n in version["numbers"].split("."))
    suffix = version["suffix"]
    # No suffix (a final version) sorts after any suffix of the same numbers.
    return numbers, suffix == "", suffix, match["date"] or ""


def main(argv):
    dry = "--dry-run" in argv
    paths = [a for a in argv if a != "--dry-run"]
    if len(paths) != 1:
        sys.exit("prune_dist.py [--dry-run] DIST")
    dist = paths[0]
    if not os.path.isdir(dist):
        return
    releases = {}
    for name in sorted(os.listdir(dist)):
        match = ARCHIVE.match(name)
        if match:
            releases.setdefault(match["name"], []).append(match)
    for matches in releases.values():
        matches.sort(key=order)
        for old in matches[:-1]:
            for name in (old.string, old.string + ".sha256"):
                path = os.path.join(dist, name)
                if os.path.exists(path):
                    print(("would remove " if dry else "removed ") + name)
                    if not dry:
                        os.remove(path)


if __name__ == "__main__":
    main(sys.argv[1:])
