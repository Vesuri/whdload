exec(open(__file__.replace('test_endpoint_ground_span_c.py','test_endpoint_ground_c.py')).read().split('resets=notifications=0')[0])
for span in [0,2,15,18,21,65535]:
 c.put(owner,bytes(164));c.put(owner+158,struct.pack('>HH',span,span));c.put(event,bytes(4));c.put(p,bytes(86))
 before=c.get(owner,164),c.get(p,86),c.get(event,4)
 assert call('endpoint_ground_resolve',{1:owner,2:p,3:stages,4:ground,5:event})==0xffffffff
 assert before==(c.get(owner,164),c.get(p,86),c.get(event,4))
print(dict(invalid_spans=6,atomic_rejection=True));c.close()
