#!/usr/bin/env python3
import argparse,os,re,struct,json
from pathlib import Path
from gpc_report import regions
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('listing',type=Path);a=p.parse_args();m=json.loads((a.capture/'metadata.json').read_text());os.environ['SLAVE']=str(a.capture/'slave.slave');d=(a.capture/'before.bin').read_bytes();sb=next(lo for lo,hi,n,o in regions(d,m['base']) if n=='slave')
s=a.listing.read_text(encoding='latin1');tail=s[s.index('verify_sim_results:\n'):];off=int(re.search(r'00:([0-9A-F]+)',tail)[1],16);result=struct.unpack_from('>II',d,sb+off-m['base']);print('guest arithmetic assertions, failures:',result);assert result[0] in (35,39,45,46,47,51,63,81) and result[1]==0
