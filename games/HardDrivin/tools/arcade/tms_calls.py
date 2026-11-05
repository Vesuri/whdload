"""Split a TMS34010 listing into functions at MMTM SP prologues and print each
function's direct calls (CALLR/CALLA), with float-library calls named.
Usage: tms_calls.py LISTING [FUNC_ADDR...]"""
import re,sys
FLIB={'74B400':'fmul','74B600':'fdiv','74C0A0':'fadd','74C000':'fsub','74DE00':'fneg','74D260':'i2f','74CE00':'f2i',
 '74D620':'fcmp2','74D640':'fcmp3','74D660':'fcmp4'}
lines=[l.rstrip('\n') for l in open(sys.argv[1])]
funcs={};cur=None
for l in lines:
 a=l[:8]
 if 'MMTM   SP' in l or cur is None:cur=a;funcs[cur]=[]
 funcs[cur].append(l)
want=sys.argv[2:] or sorted(funcs)
for f in want:
 body=funcs.get(f.upper().zfill(8))
 if not body:print(f,'not a function start');continue
 calls=[re.search(r'CALL[AR] +([0-9A-F]+)h',l).group(1) for l in body if re.search(r'CALL[AR] +[0-9A-F]+h',l)]
 named=[FLIB.get(c[-6:],c) for c in calls]
 g=[x for x in named if not x.startswith('f') and not x.startswith('i2')]
 print('%s len %4d flops %3d calls: %s'%(f,len(body),len(named)-len(g),' '.join(dict.fromkeys(g))))
