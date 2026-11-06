# TFX executables

Checked with `tools/hunkinfo.py` (hunk structure; relocations whose stored value
exceeds the target hunk size are "implausible") and `tools/relocdiff.py`.
A clean file has 0 implausible relocations; `tfx.020` (also Hunk Wizard output) has 0.

| File | Size | Build stamp | Kind | State |
|---|---|---|---|---|
| `TFX` | 554340 | Feb 13 1995 18:19:11 | integer (no FPU) | clean, slave default |
| `TFX.FPU` | 503340 | – | 68881 FPU | clean |
| `TFX.040` (slave name) | 599152 | – | 68881 FPU, symbols | clean; not a 68040 build |
| `tfx.floppy` | 555644 | Dec 8 1994 | integer | clean |
| `tfx.020` | 571008 | Dec 16 1997 21:57:21 | 68881 FPU | clean, newest intact build |
| `tfx.030` | 570480 | – | 68881 FPU | damaged from file offset 0x42200 |
| `tfx.strip` ("040" beta) | 571008 | Dec 16 1997 00:20:49 | 68881 FPU | damaged from 0x4b200 |
| `tfx.exe` (CD #15 LZX) | 709968 | Feb 13 1995 18:19:16 | integer | damaged from 0x27400 |

- `tfx.strip`: header, hunk sizes and full reloc table are identical to `tfx.020`;
  883/1116 512-byte blocks are identical in place, 230 are copies of other `tfx.020`
  blocks (mostly shifted by 15 blocks, some zero blocks), 3 unique. Filesystem-style
  block damage of a build whose code layout equals `tfx.020`. Nothing 040-specific in it.
- `tfx.030`: separate build, same damage pattern (blocks after 0x42200).
- CU Amiga Super CD-ROM #15 `TFX/` has launcher `TFX_040` running `TFX.040`, but no
  such file on the CD. The 720K-floppy LZX contains `tfx.exe`, the size the slave's
  disabled `v040_orig` expects; built 5 s after `TFX`, integer code, 59% of relocs
  implausible, 111 zero blocks. Archive CRCs pass, so damage predates the CD.
- The 1997 zips (oocities mirror of Charlie Wallace's GeoCities site) pass CRC too.

Open leads: Wayback captures of geocities.com/CapeCanaveral/7992 (archive.org was
offline when checked); EAB users reported a working renamed `tfx.strip`.

Downloads: `tmp/dl040/` (zips + `zips.sha256`), `tmp/cd15/` (CD #15 files via
archive.org ISO browsing; joined `TFX.lzx`, extraction in `x/TFX/`).
CD #15 readme (`readme.tfx`, 1994 bug report) lists bugs 30/67 "colours mess up"
as unresolved.
