"""Compare two plan step F matrices record for record (plan step G4).

compare_feel_records.py OLD_ROOT NEW_ROOT

For every run in OLD_ROOT (tmp/prof/OLD_ROOT/NAME), rec.bin (one record per
field) and steps.bin (the pose at every physics return) must be byte-identical
in NEW_ROOT. Prints one line per run and a total; exits nonzero on any
difference or missing run.
"""
import sys
from pathlib import Path

PROF = Path(__file__).resolve().parents[1] / 'tmp/prof'


def main():
    old, new = PROF / sys.argv[1], PROF / sys.argv[2]
    runs = sorted(p.name for p in old.iterdir() if (p / 'rec.bin').exists())
    same = 0
    for name in runs:
        verdict = []
        for f in ('rec.bin', 'steps.bin'):
            a, b = old / name / f, new / name / f
            if not b.exists():
                verdict.append('%s missing' % f)
                continue
            x, y = a.read_bytes(), b.read_bytes()
            if x != y:
                first = next((i for i in range(min(len(x), len(y))) if x[i] != y[i]), min(len(x), len(y)))
                verdict.append('%s differs at byte %d (%d vs %d bytes)' % (f, first, len(x), len(y)))
        if verdict:
            print('%-18s %s' % (name, '; '.join(verdict)))
        else:
            same += 1
            print('%-18s identical (%d records, %d returns)' % (
                name, (old / name / 'rec.bin').stat().st_size // 80, (old / name / 'steps.bin').stat().st_size // 92))
    print('%d of %d runs identical' % (same, len(runs)))
    sys.exit(0 if same == len(runs) else 1)


if __name__ == '__main__':
    main()
