"""Offline diagnostic: change only prescribed zero-gravity contact motion."""
from contact_body_predictor import body,wheel
from native_contact_event_probe import respond

def solve(entry,build,rows,state):
    def event_wheel(row):
        out=wheel(row)
        if row['velocity'] or row['velocity_fraction'] or row['correction'] or row['clearance']>0:
            return out
        old=[row['old_world_'+a] for a in 'xyz']
        result=respond(old,row['distance'],entry[10:13],state['cached'][row['wheel']])
        if result is None:return out
        out.update(position=result['position'],clearance=result['clearance'],
                   velocity=0,vf=0,pf=0,ef=0,branch='event_tangent',
                   event_time=result['time'],event_push=result['push'])
        # Suspension still uses the native pre-response sampled clearance.
        # Force activation is deliberately unchanged in this diagnostic.
        return out
    return body(entry,build,rows,wheel_solver=event_wheel)
