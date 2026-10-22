"""Verify input bytes only; no code analysis or emulator execution."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    for entry in json.loads((ROOT / "manifest/inputs.json").read_text()):
        archive = ROOT / "tmp/archives" / entry["name"]
        if sha256(archive) != entry["sha256"]:
            raise ValueError("Archive mismatch: " + entry["name"])
        tree = ROOT / entry["extraction"]
        expected = json.loads((ROOT / entry["files_manifest"]).read_text())
        actual = {p.relative_to(tree).as_posix(): sha256(p)
                  for p in sorted(tree.rglob("*")) if p.is_file()}
        if actual != expected:
            raise ValueError("Extracted files differ: " + entry["name"])
        print(entry["name"] + ": archive and " + str(len(actual)) + " files verified")

if __name__ == "__main__":
    main()
