#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
. tools/env.sh
out="$PWD/tmp/step6"
headless="${GHIDRA_HEADLESS:-$(brew --prefix ghidra)/libexec/support/analyzeHeadless}"
export JAVA_HOME="${JAVA_HOME:-$(brew --prefix openjdk@21)/libexec/openjdk.jdk/Contents/Home}"
mkdir -p "$out/java-home"
export JAVA_TOOL_OPTIONS="-Duser.home=$out/java-home"
"$headless" "$out" ghidra -import "$out/tfx.020-0.bin" -overwrite \
 -processor 68000:BE:32:MC68020 -loader BinaryLoader -noanalysis \
 -scriptPath "$PWD/tools;$AMIGA_GHIDRA_SCRIPTS" \
 -postScript ApplyTfxNames.java "$out/symbols.csv" "$out/entries.txt" \
 -postScript ExportAuditListing.java "$out/ghidra-audit.txt" \
 -postScript DumpCallGraph.java "$out/ghidra-callgraph.txt" \
 -log "$out/ghidra-audit.log" > "$out/ghidra-console.txt" 2>&1
# Headless can return zero after a script error: require success markers.
rg -q 'TFX labels applied:' "$out/ghidra-console.txt"
rg -q '37 functions' "$out/ghidra-audit.txt"
if rg -q 'ERROR|Exception' "$out/ghidra-console.txt"; then exit 1; fi
