#!/usr/bin/env python3
"""Apply the retained, validated patch to a fresh step4 metadata-observer copy."""
import subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
subprocess.run(['patch','--dry-run','-p1','-i',str(root/'tools/040-cost-observer.patch')],cwd=sys.argv[1],check=True)
subprocess.run(['patch','-p1','-i',str(root/'tools/040-cost-observer.patch')],cwd=sys.argv[1],check=True)
