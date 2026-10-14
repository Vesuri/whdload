"""E2 native-keyboard campaign checkpoints; no guest code or state injection."""

def run(out, layout, command, until, key, dump, capture, build):
    h=layout['hunks'][0]
    def number(expr):
        reply=command('printf "VALUE %u\\n", '+expr)
        return int(reply.split('VALUE ')[1].split()[0])
    def type_name(codes, end, label):
        for code in codes:
            key(1,code)
            until(h+0x16a86,label+' character accepted')
            key(0,code)
            until(h+0x16992,label+' input ready')
        address=number('$a3');length=number('$d3')
        data=dump(label+'-text.bin',address,address+length)
        if data.lower()!=b'test':raise ValueError('name editing failed: '+repr(data))
        key(1,'44');until(h+end,label+' submitted');key(0,'44')
    # Enter TEST, delete its last letter, then restore it.
    type_name(('14','12','21','14','41','14'),0x16c40,'surname')
    until(h+0x16992,'callsign input')
    type_name(('14','12','21','14'),0x16c66,'callsign')
    until(h+0x171c4,'scoreboard input')
    key(1,'45');until(h+0x17228,'scoreboard dismissed');key(0,'45')
    until(h+0x24f28,'bar pointer loop')
    until(h+0x24f28,'bar settled',f'*(unsigned int*)($a4-0x800) >= {number("*(unsigned int*)($a4-0x800)")+10}')
    capture('bar')
    # Move the native keyboard pointer to the barracks door.
    key(1,'4e')
    until(h+0x24f28,'bar right door','*(short*)($a4+0x19c) >= 300')
    key(0,'4e')
    key(1,'44');until(h+0x24ffe,'barracks chosen');key(0,'44')
    until(h+0x26134,'barracks pointer loop')
    until(h+0x26134,'barracks settled',f'*(unsigned int*)($a4-0x800) >= {number("*(unsigned int*)($a4-0x800)")+10}')
    capture('barracks')
    def point(x,y):
        for off,target,negative,positive in ((0x19c,x,'4f','4e'),(0x19e,y,'4c','4d')):
            current=number(f'*(unsigned short*)($a4+{off})')
            if abs(current-target)<=2:continue
            direction=positive if current<target else negative
            key(1,direction)
            relation='>=' if current<target else '<='
            step=5 if off==0x19c else 3
            threshold=target-step if current<target else target+step
            until(h+0x26134,'barracks pointer positioned',f'*(short*)($a4+{off}) {relation} {threshold}')
            key(0,direction)
            until(h+0x26134,'pointer release settled',f'*(unsigned int*)($a4-0x800) >= {number("*(unsigned int*)($a4-0x800)")+2}')
        dump(f'pointer-{x}-{y}.bin',layout['a4']+0x19c,layout['a4']+0x1a0)
    point(142,91)
    key(1,'44');until(h+0x25e98,'save completed');key(0,'44')
    if not number('$d0'):raise ValueError('native save failed')
    slot=number('$a2');saved=dump('saved-slot.bin',slot,slot+0x37e)
    until(h+0x26134,'saved bunk ready');capture('saved')
    point(116,91)
    key(1,'44');until(h+0x258bc,'load confirmation');key(0,'44')
    key(1,'15');until(h+0x25ee0,'load completed');key(0,'15')
    a4=layout['a4']
    actual=dump('loaded-player.bin',a4+0x876,a4+0x876+70)
    if actual!=saved[0x158:0x19e]:raise ValueError('loaded player differs from saved slot')
    actual=dump('loaded-campaign.bin',a4+0x3bf2,a4+0x3bf2+342)
    if actual!=saved[2:0x158]:raise ValueError('loaded campaign differs from saved slot')
    actual=dump('loaded-state.bin',a4+0x131c,a4+0x131c+480)
    if actual!=saved[0x19e:]:raise ValueError('loaded state differs from saved slot')
    until(h+0x26134,'loaded bunk ready');capture('loaded')
    point(300,60)
    key(1,'44');until(h+0x26228,'mission hangar chosen');key(0,'44')
    until(h+0x1d2b0,'mission briefing entry')
    key(1,'45');until(h+0x694,'campaign flight');key(0,'45')
    capture('campaign')
    sb=layout['slave'];sy=build['symbols'];iteration=sb+sy['ocs_clock_iteration']
    windows=[];labels=['bar','barracks','saved','loaded','campaign']
    def window(label,fields=100):
        command(f'monitor ocs-window {fields} 1 {h:x} {layout["hunks"][1]:x} "{out}/{label}-events.txt"',timeout=180)
        capture(label);windows.append(dict(label=label,fields=fields));labels.append(label)
    until(iteration,'campaign clock active')
    window('campaign-coast')
    # F9 cycles the external-camera subject; the carrier selects mode 8.
    for slot,view in ((1,4),(2,8)):
        key(1,'58')
        until(h+0x73f8,f'external subject {slot}',f'*(short*)($a4-0x479e) == {slot} && *(short*)($a4-18318) == {view}')
        key(0,'58');window(f'campaign-subject{slot}')
    key(1,'50');until(h+0x73f8,'front view restored','*(short*)($a4-18318) == 0');key(0,'50')
    key(1,'20');until(sb+sy['ocs_clock_original_autopilot'],'native autopilot entered');key(0,'20')
    until(iteration,'autopilot returned to flight')
    # Native target builder O:37c6 excludes contacts at range >=12000.
    until(h+0x3860,'contact enters native targeting range','$d3 > 0')
    until(iteration,'contact selection settled')
    window('campaign-combat',150)
    key(1,'14');until(h+0x188e6,'native target selection');key(0,'14')
    until(iteration,'target selection settled')
    if number('*(unsigned char*)($a4+0xcea)')==255:raise ValueError('target view needs a selected contact')
    key(1,'56');until(h+0x73f8,'campaign view 7 selected','*(short*)($a4-18318) == 7');key(0,'56')
    window('campaign-view7')
    for raw,view in (('51',2),('52',1),('53',3),('54',4),('55',14),('50',0)):
        key(1,raw)
        until(h+0x73f8,f'campaign view {view} selected',f'*(short*)($a4-18318) == {view}')
        key(0,raw);window(f'campaign-view{view}')
    key(1,'57');until(h+0x1898a,'missile camera enabled');key(0,'57')
    if number('*(unsigned short*)($a4-0x4772)')!=1:raise ValueError('missile follow not enabled')
    key(1,'44');until(h+0x73f8,'missile camera entered','*(short*)($a4-18318) == 6');key(0,'44')
    window('campaign-view6',40)
    key(1,'50');until(h+0x73f8,'front view after missile','*(short*)($a4-18318) == 0');key(0,'50')
    for raw,label in (('40','campaign-fire'),('4e','campaign-turn'),('42','campaign-afterburner')):
        key(1,raw);window(label);key(0,raw)
    key(1,'19');until(h+0x87c,'native pause active');key(0,'19')
    count=number(f'*(unsigned int*){sb+sy["ocs_clock_completed"]}')
    before=dump('pause-before.bin',layout['hunks'][1],layout['hunks'][1]+0xf5b8)
    command(f'monitor ocs-window 20 1 {h:x} {layout["hunks"][1]:x} "{out}/pause-events.txt"',timeout=60)
    after=dump('pause-after.bin',layout['hunks'][1],layout['hunks'][1]+0xf5b8)
    for offset,size in ((0x8928,61*12),(0x94fa,61*12),(0x8e8c,61*2)):
        if before[offset:offset+size]!=after[offset:offset+size]:raise ValueError('world changed during pause')
    if number(f'*(unsigned int*){sb+sy["ocs_clock_completed"]}')!=count:raise ValueError('world tick during pause')
    key(1,'19');until(h+0x8b0,'native pause resumed');key(0,'19')
    until(iteration,'resumed flight clock')
    window('campaign-resumed')
    # The original WHDLoad quit key flushes its buffered save writes to this
    # run's disposable host game tree. It is separate from campaign ejection.
    key(1,'5d')
    command(f'monitor ocs-window 100 0 {h:x} {layout["hunks"][1]:x} "{out}/quit-events.txt"',timeout=120)
    command(f'monitor profile 2 "" "{out}/quit-screen.bin"',timeout=120)
    key(0,'5d')
    from amigaxdev import barto
    trace=barto.load(str(out/'quit-screen.bin'))
    (out/'quit.png').write_bytes(trace.fields[-1].shot)
    return {'checkpoints':labels,'windows':windows,'name_editing':True,'save_load':True,'pause_fields':20,'quit_key':True}
