#!/usr/bin/env python3
"""E2 compatibility evidence: native UI state, persistent saves and display ownership.
No speed recommendation or full-campaign/hardware claim follows from this gate.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import wc_run
from PIL import Image
from ocs_publication_report import report as publication, window
from ocs_baseline_report import parse
from ocs_reconstruct import new_output, require


def report(root, build):
    m=json.loads((root/'result.json').read_text())
    b=json.loads((build/'build.json').read_text());sy=b['symbols']
    result=publication(root,build)
    def own(label,name,size=4):
        raw=(root/f'{label}-fast.bin').read_bytes()
        offset=m['slave']-0x200000+sy[name]
        return int.from_bytes(raw[offset:offset+size],'big')
    standard=m.get('video_standard','PAL');hz=60 if standard=='NTSC' else 50
    require(own('fire','ocs_clock_hz')==hz,'wrong detected field standard')
    for label in ('menu','name'):
        require(own(label,'ocs_clock_active',2)==0 and own(label,'intro_active',2)==0,
                'active world clock in menu/name')
    require(own('credits','ocs_intro_completed')==296,'incomplete title world sequence')
    require(own('fire','ocs_input_overflows')==own('fire','ocs_input_missing')==0,'input history loss')
    rows=parse(root/'fire-events.txt');first=rows[0];last=next(r for r in rows if r[0]=='E')
    fields=[r for r in rows if r[0]=='F']
    require(first[0]=='B' and first[2]==(28636360 if hz==60 else 28375160),'master clock mismatch')
    require(last[1]==fields[-1][1],'live denominator after frozen field endpoint')
    periods={y[1]-x[1] for x,y in zip(fields,fields[1:])}
    # NTSC alternates 227/228-clock lines (custom.cpp hsync lol);
    # an odd 263-line field therefore alternates its rounded duration.
    expected=({n*512 for n in (59605,59832,59833)} if hz==60 else
              {227*n*512 for n in (312,313)})
    require(periods<=expected,'wrong physical field period')
    ticks=sum(r[0]=='P' and r[2]==0x2dc for r in rows)
    require(ticks==((fields[-1][3]-first[5])&65535),'world tick accounting disagreement')
    result['clock']=dict(standard=standard,configured_hz=hz,fields=len(fields),ticks=ticks,
                         target_ticks=len(fields)*10/hz,scope='field/counter accounting, not a performance acceptance')
    if m['effective']['chipset']=='aga':
        audits=[]
        for label in m['checkpoints']:
            raw=(root/f'{label}-cpu.txt').read_text()
            values=dict(re.findall(r'(\w+)=(\w+)',raw))
            require(values.get('model')=='68020' and values.get('unit')=='64' and
                    int(values['cacr'],16)&1,'accelerated instruction-cache model absent')
            audits.append(label)
        result['cache']=dict(instruction_cache=True,checked=audits,data_cache='68020 has none')
    if m.get('functional') and 'windows' not in m['functional']:
        result['partial_ui_scope']='Name/bar/barracks checkpoints only; no full functional acceptance'
    if m.get('functional',{}).get('windows'):
        f=m['functional'];checks={}
        expected_labels={'campaign-coast','campaign-combat','campaign-view7',
                         'campaign-fire','campaign-turn','campaign-afterburner','campaign-resumed',
                         'campaign-subject1','campaign-subject2','campaign-view6'}
        expected_labels|={f'campaign-view{i}' for i in (0,1,2,3,4,14)}
        require({w['label'] for w in f['windows']}==expected_labels,'functional window coverage incomplete')
        for w in f['windows']:
            label=w['label'];checks[label]=window(parse(root/(label+'-events.txt')),w['fields'])
            require(own(label,'ocs_clock_active',2)==1,'flight clock inactive')
            if '-view' in label:
                data=(root/f'{label}-h1.bin').read_bytes()
                require(int.from_bytes(data[0x3870:0x3872],'big')==int(label.split('view')[1]),'wrong camera')
        for slot,view in ((1,4),(2,8)):
            data=(root/f'campaign-subject{slot}-h1.bin').read_bytes()
            require(int.from_bytes(data[0x3860:0x3862],'big')==slot and
                    int.from_bytes(data[0x3870:0x3872],'big')==view,'external camera subject mismatch')
        for label in ('surname','callsign'):
            require((root/f'{label}-text.bin').read_bytes().lower()==b'test','name edit/submission missing')
        for label in ('bar','barracks','saved','loaded'):
            require(own(label,'ocs_clock_active',2)==own(label,'intro_active',2)==0,'world clock leaked across scene')
            with Image.open(root/f'{label}.png') as im:
                require(len(im.convert('RGB').getcolors(1000000) or [])>16,'empty UI capture')
        saved=(root/'saved-slot.bin').read_bytes()
        require(len(saved)==894 and saved[0]==1,'invalid saved slot')
        require((root/'loaded-player.bin').read_bytes()==saved[0x158:0x19e] and
                (root/'loaded-campaign.bin').read_bytes()==saved[2:0x158] and
                (root/'loaded-state.bin').read_bytes()==saved[0x19e:],'save/load record mismatch')
        files=list(wc_run.capture_drawer(root).glob('data/SAVEGAME.WLD'))
        require(len(files)==1,'save was not flushed on quit')
        disk=files[0].read_bytes()
        require(len(disk)==8*894 and disk[:894]==saved,'persistent save differs from loaded slot')
        before=(root/'pause-before.bin').read_bytes();after=(root/'pause-after.bin').read_bytes()
        for offset,size in ((0x8928,61*12),(0x94fa,61*12),(0x8e8c,61*2),(0x88da,2)):
            require(before[offset:offset+size]==after[offset:offset+size],'world advanced during pause')
        paused=parse(root/'pause-events.txt')
        require(len([r for r in paused if r[0]=='F'])==20 and
                not any(r[0]=='P' and r[2]==0x2dc for r in paused),'pause field/tick evidence missing')
        fire=(root/'campaign-fire-h1.bin').read_bytes();turn=(root/'campaign-turn-h1.bin').read_bytes()
        burn=(root/'campaign-afterburner-h1.bin').read_bytes()
        require(any(fire[o:o+12]!=turn[o:o+12] for o in (0x98d6,0xaa3e,0xad3e)),'steering did not rotate player')
        require(int.from_bytes(burn[0x9cda:0x9cde],'big')<int.from_bytes(turn[0x9cda:0x9cde],'big'),'afterburner did not spend fuel')
        require(any(int.from_bytes(fire[0x8e8c+2*i:0x8e8e+2*i],'big')==8 for i in range(1,61)),'fire did not produce projectiles')
        result['functional']=dict(windows=checks,name_editing=True,save_load=True,
            persistent_save_sha256=hashlib.sha256(disk).hexdigest(),pause_fields=20,
            quit='original WHDLoad key, save flush; inspect quit.png for AmigaDOS return',
            controls=['keyboard','fire','steering','afterburner','pause/resume'],
            limitations=['bounded first-mission route, not full campaign','no physical input-device or hardware acceptance'])
    return result


def negative_controls(root, build, out):
    """Reject corrupted records independently of native execution success."""
    cases=[('wrong-field-standard','result.json',None)]
    metadata=json.loads((root/'result.json').read_text())
    if metadata.get('functional',{}).get('windows'):
        cases += [('wrong-loaded-record','loaded-state.bin',0),
                  ('wrong-target-view','campaign-view7-h1.bin',0x3871),
                  ('world-moved-during-pause','pause-after.bin',0x892b)]
    rejected=[]
    for name,filename,offset in cases:
        scratch=out/name;scratch.mkdir()
        for path in root.iterdir():
            (scratch/path.name).symlink_to(path.resolve(),target_is_directory=path.is_dir())
        target=scratch/filename;data=target.read_bytes();target.unlink()
        if offset is None:
            value=json.loads(data);value['video_standard']='PAL' if value.get('video_standard')=='NTSC' else 'NTSC'
            data=json.dumps(value).encode()
        else:
            value=bytearray(data);value[offset]^=1;data=bytes(value)
        target.write_bytes(data)
        try:report(scratch,build)
        except ValueError:rejected.append(name)
        else:raise ValueError('corrupt compatibility evidence accepted: '+name)
    return rejected


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path);p.add_argument('--build',required=True,type=Path);p.add_argument('--output',required=True)
    a=p.parse_args();result=report(a.run,a.build)
    out=new_output(a.output);out.mkdir(parents=True)
    result['rejected_controls']=negative_controls(a.run,a.build,out)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Compatibility/state checks passed; functional route:',bool(result.get('functional')))

if __name__=='__main__':main()
