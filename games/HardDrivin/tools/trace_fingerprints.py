import hashlib,json
import barto_mmap as bm
def fingerprint(out):
 t=bm.load(out/'trace.bin');result=[]
 for f in t.fields:
  result.append(dict(index=f.index,cycles=f.cycles,instructions=hashlib.sha256(t.data[f.insn_off:f.insn_end]).hexdigest(),dma=hashlib.sha256(f.dma).hexdigest(),screenshot=hashlib.sha256(f.shot).hexdigest()))
 (out/'trace-fingerprints.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
