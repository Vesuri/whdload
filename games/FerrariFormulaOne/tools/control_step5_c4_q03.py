from pathlib import Path
import socket,sys,json
r=Path(__file__).resolve().parents[1]
items=json.loads(Path(sys.argv[1]).read_text()) if sys.argv[1].endswith('.json') else json.loads(sys.argv[1])
if isinstance(items,dict):items=[items]
for request in items:
 with socket.socket(socket.AF_UNIX) as client:
  client.settimeout(180);client.connect(str(r/'tmp/run/default/.run/q03-modal.sock'));client.sendall((json.dumps(request)+'\n').encode());data=b''
  while not data.endswith(b'\n'):data+=client.recv(65536)
  answer=json.loads(data)
  if 'error' in answer:answer['error']=answer['error'][:2000]
  print(json.dumps(answer),flush=True)
  if 'error' in answer:raise RuntimeError(answer)
