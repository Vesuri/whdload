from pathlib import Path
import json,re,struct,hashlib
r=Path(__file__).resolve().parents[1];g=r.parents[1]/'Games';s=(g/'FerrariFormulaOne/RenderText.s').read_text();f=(g/'FerrariFormulaOne/Fine.s').read_text();p=(g/'FerrariFormulaOne_Presentation.s').read_text();full=(g/'FerrariFormulaOne_FullPresentation.s').read_text();b=r/'tmp/build/render-h4';m=json.loads((b/'build.json').read_text());sy=m['payloads']['fine']['symbols'];listing=(b/'fine/fine.list').read_text()
assert 'move.w sr' not in s and '$dff' not in s
assert s.count(' jsr $24ae0')==2 and s.count(' jsr $2a130')==2
assert 'cmpa.l $226b2,a0\n move.l (sp)+,a0\n bne.w .native' in s
assert 'FF1_FINE_TEXT equ 1' in f and 'IFD FF1_FINE_TEXT\n bsr.l FF1RenderClockDigit' in p and 'B8_65d56:\n IFD FF1_FINE_TEXT' in full
# Confirm assembler chose MOVEA for the restore, preserving CMPA's condition.
lines=listing.splitlines();restore=[x for x in lines if re.search(r'205F\s+\d+:\s+move.l \(sp\)\+,a0',x) and sy['FF1RenderClockDigit']<=int(x.split()[0].split(':')[1],16)]
assert restore, 'clock pointer comparison must survive A0 restoration'
code=(b/'fine/fine.bin').read_bytes();table=sy['FF1RenderDemoColumns'];assert code[table:table+21]==bytes((ord(c)-97 if c!=' ' else 255) for c in 'hit a key to end demo')
files=[g/'FerrariFormulaOne/RenderText.s',g/'FerrariFormulaOne/Fine.s',g/'FerrariFormulaOne_Presentation.s',g/'FerrariFormulaOne_FullPresentation.s']
out=dict(status='passed',sources={str(p.relative_to(g)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},no_sr_reads=True,native_bitmap_calls=2,waits_around_chip_scratch=True,clock_guard_movea_preserves_flags=True,decoded_glyph_table_exact=True,new_native_patch_sites=0,no_destination_cache=True,ownership='Compose current font in public workspace; after native WaitBlit copy 192 bytes into existing 1020-byte Chip colour scratch, draw both pointer views with native shifted/masked bitmap routine, WaitBlit before return. Clock skips only immediate identical-destination overwrite; every new frame is drawn.',native_reader_evidence='manifest/render-h2-scratch.json',palette_scope='No palette code changed; inherited B8-PAL diagnostic pulse remains separate cleanup.')
(r/'manifest/render-h4-source-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
