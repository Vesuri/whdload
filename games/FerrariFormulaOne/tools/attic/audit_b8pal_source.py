from pathlib import Path
import json,subprocess,hashlib
r=Path(__file__).resolve().parents[1];root=r.parents[1];fn='Games/FerrariFormulaOne_FullPresentation.s';old=subprocess.check_output(['git','show','HEAD:'+fn]).decode();new=(root/fn).read_text();assert old.replace(' move.w d1,$dff180\n','; No inherited diagnostic COLOR00 pulse; ext.l already supplies the flags.\n')==new
assert '$dff180' not in new.lower();host='Games/FerrariFormulaOne_WHD.s';assert (root/host).read_bytes()==subprocess.check_output(['git','show','HEAD:'+host])
# EXT.L sign-extends D1.w and sets NZVC; the removed MOVE.W uses that same word.
for word in range(65536):
 extended=word if word<32768 else word|0xffff0000
 assert (extended==0, bool(extended&0x80000000))==(word==0,bool(word&0x8000))
a=r/'tmp/build/render-h11-v2';b=r/'tmp/build/render-b8pal';meta=json.loads((b/'build.json').read_text());regions={}
for kind in ['000','020','fine']:
 def region(base):
  m=json.loads((base/'build.json').read_text())['payloads'][kind];sy=m['symbols'];return (base/kind/'payload.bin').read_bytes()[sy['B8_65518']:sy['B8_6551e']]
 before=region(a);after=region(b);assert before==after+bytes.fromhex('33c100dff180'),(kind,before.hex(),after.hex())
 regions[kind]={'before':before.hex(),'after':after.hex(),'removed_bytes':6}
out={'status':'passed','only_source_change':'Remove inherited COLOR00 diagnostic write from shared B8 renderer','compiled_regions':regions,'ccr_equivalence_word_cases':65536,'ccr_details':'EXT.L and removed MOVE.W produce identical N/Z, clear V/C, preserve X for all sign-extended D1 words.','legacy_host_source_unchanged':True,'all_performance_payloads_affected':True,'no_dma_palette_buffer_or_lifecycle_logic_changed':True,'production_bytes':meta['bytes'],'production_sha256':hashlib.sha256((b/'FerrariFormulaOne.slave').read_bytes()).hexdigest()};(r/'manifest/b8-pal-source-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
