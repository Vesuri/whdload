from pathlib import Path
import re
src=Path('src')
p=src/'simulation.s';s=p.read_text();s='''; Fixed 20 ms PAL simulation steps, selected by CUSTOM2 and CPU/Fast RAM.
; Rendering remains vsynced and runs as fast as possible. Rider-heading
; prediction affects display only. Input history exhaustion aborts explicitly.

'''+s[s.index('; Select only'):]
s=s.replace('; Reason: 0 disabled, 1 CPU, 2 memory placement, 3 selected. Return d0=0/1.','; Save the selected path for relocation/HUD setup. Return d0=0/1.')
a=s.index('step_select_path:');b=s.index('\tIFND STEP_FIELDS',a)
s=s[:a]+'''step_select_path:
	lea enhanced_selected(pc),a0
	clr.l (a0)
	move.l _enhanced_framerate(pc),d0
	beq .no
	move.l cpu_attention(pc),d1
	btst #1,d1
	beq .no
	lea _base(pc),a1
	cmpa.l #$200000,a1
	bcs .no
	cmpa.l #$a00000,a1
	bcs .yes
	cmpa.l #$1000000,a1
	bcs .no
.yes:
	move.l #3,(a0)
	moveq #1,d0
	rts
.no:
	moveq #0,d0
	rts

'''+s[b:]
s=s.replace('\tlea step_stats(pc),a0\n\tmove.l d0,8(a0)\n\tclr.l 12(a0)\n\tclr.l 16(a0)','\tlea step_cursor(pc),a0\n\tmove.l d0,(a0)')
s=s.replace('step_stats+8(pc)','step_cursor(pc)').replace('step_stats(pc)','step_cursor(pc)')
s=s.replace('\tlea step_cursor(pc),a0\n\tmove.l 8(a0),d0','\tlea step_cursor(pc),a0\n\tmove.l (a0),d0')
s=s.replace('\tmove.l d0,8(a0)\n\tmove.l d0,$a5d50','\tmove.l d0,(a0)\n\tmove.l d0,$a5d50')
s=s.replace('\taddq.l #1,12(a0)\n','')
s=s.replace("step_stats:\n\tdc.b 'RRCSTEP1'\n\tdc.l 0,0,0,STEP_FIELDS",'step_cursor:\n\tdc.l 0')
s=re.sub(r'\tIFND POSE_PREDICT_FIELDS\nPOSE_PREDICT_FIELDS = 3\n\tENDC\n','',s)
s=s.replace('; Keep diagnostic patch targets within the WHDLoad signed-word reach and','; Keep patch targets within the WHDLoad signed-word reach and').replace('; 68000-compatible instructions. Repeat per field for larger diagnostic quanta.','; 68000-compatible instructions.').replace('; Runtime uses the measured render interval; diagnostics can fix the horizon.','; Use the measured render interval for heading prediction.').replace('; Preserve the measured normal-runtime layout independently of diagnostics.','; Keep these helpers within PC-relative reach of their callers.')
p.write_text(s)
p=src/'RoadRashHD.s';s=p.read_text().replace('verify_c_selection:\n\tdc.b "RRCSEL01"\n\tdc.l 0,0,0,0','enhanced_selected:\n\tdc.l 0');p.write_text(s)
p=src/'runtime_stack.s';s=p.read_text();s=s.replace('\tlea step_stack_stats(pc),a0\n\taddq.l #1,12(a0)\n\tlea 16(a1),a1\n\tmove.l a1,16(a0)\n\tlea STEP_STACK_SIZE(a1),a1\n\tmove.l a1,20(a0)','\tlea step_stack_top(pc),a0\n\tlea 16+STEP_STACK_SIZE(a1),a1\n\tmove.l a1,(a0)').replace('step_stack_stats+20(pc)','step_stack_top(pc)').replace('step_stack_stats:\n\tdc.b "RRCSTK01"\n\tdc.l STEP_STACK_SIZE,0,0,0 ; size, initialization count, bottom, top','step_stack_top:\n\tdc.l 0');p.write_text(s)
for p in src.glob('*.s'):
 s=p.read_text().replace('verify_c_selection+20','enhanced_selected').replace('verify_attn','cpu_attention')
 s=s.replace('See simulation-timing.md for the copy audit.','').replace('See simulation-timing.md for the audit.','').replace('See memory-performance.md.','')
 s='\n'.join(line for line in s.splitlines() if not any(x in line for x in ('Snapshot diagnostics','Full snapshot diagnostics','diagnostic control','Optional diagnostics','broader D3 module/data audit','Normal runtime selects this after full finish','hardware, response and restart checks.')))+'\n'
 s=re.sub(r'; (?:F[1-6][a-z]?|E[1-6](?:/E[1-6])?): ', '; ',s)
 s=s.replace('after any selected C copy initializers','after the simulation copy initializers').replace('C-only copies','Simulation copies').replace('after the C patch list','after the simulation patch list')
 s=re.sub(r'\n{3,}','\n\n',s)
 p.write_text(s)
p=src/'Makefile';s=p.read_text();s=re.sub(r'^ORIGINAL.*\n|^OUT.*\n','',s,flags=re.M).replace('all dist clean','all clean');s=re.sub(r'\ndist:\n.*?\n\nclean:', '\nclean:',s,flags=re.S);p.write_text(s)
p=src.parent/'Readme';s=p.read_bytes().decode('latin1').replace('\r\n','\n');a=s.index(' With Enhanced framerate,');b=s.index('CD32 controls - menu:',a)
s=s[:a]+''' Enhanced framerate uses Fast RAM for smoother, vsynced play while keeping
 game logic at a consistent speed. It enables caches unless NoCache is set.
 A 68000 with Fast RAM benefits from rendering improvements; Chip-only
 machines and machines without suitable memory use the original path.
 Opponent paths and collision outcomes may differ with the option enabled.

'''+s[b:];p.write_bytes(s.replace('\n','\r\n').encode('latin1'))
