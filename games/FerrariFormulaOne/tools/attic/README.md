# Retired harness scripts

Moved here on 2026-11-01 when the test matrix was reduced and folded into
`tools/ff1check.py`. They are kept for provenance: older manifests and
tmp/dev/docs reports cite them as `tools/<name>`; read that as
`tools/attic/<name>`. Most were one-off investigation clones. Several still
hard-code their builds, so prefer `ff1check.py` and port a script back to
`tools/` only if a check needs it again.

1607 files.

Since the import into the WHDLoad repository these scripts keep their old paths:
`tmp/dev/` is now the game directory, `Games/FerrariFormulaOne_*.s` and
`Games/FerrariFormulaOne/` are `src/` and `tools/` (`tools/ff1layout.py` stages the old
view), `manifest/` is `tmp/manifest/` and `amiga/run.sh` is `tools/run.sh`.
