import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from check_disabled import check
from hook_ranges import ranges
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();m=json.loads((a.capture/'entry.json').read_text())
# Use the emulator's recorded RAM map, not a hard-coded machine's bank size.
banks=[]
for base,end in r.memory_regions():
 path=a.capture/f'audit-{base:x}.bin'
 r.command(f'gdb dump binary memory {path} {base:#x} {end:#x}')
 banks.append((base,path.read_bytes()))
def read(addr,size):
 for base,data in banks:
  off=addr-base
  if 0<=off and off+size<=len(data):return data[off:off+size]
 raise ValueError(hex(addr))
mask=int(re.search(r'CUSTOM2=(\d+)',m['whd_args']).group(1))
if mask & 8192:mask |= 768
spans=[s for s in ranges() if not mask & (1<<s[2])]
check(Path('tmp/game/RedBaron/data/sim').read_bytes(),m['entry']['sim'],read,spans)
lines=(a.capture/'slave.lst').read_text(errors='replace').splitlines()
def symbol(name):
 for i,line in enumerate(lines):
  if re.search(r'\b'+re.escape(name)+r':',line):
   for following in lines[i:]:
    found=re.match(r'00:([0-9A-F]+)\s',following)
    if found:return int(found[1],16)
 raise ValueError(name)
slave=m['entry']['game_anchor']-symbol('tape_game_anchor');selected=[]
for off,name,op in [(0x2c31c,'time_exp_fast',b'\x4e\xf9'),(0x15c82,'time_model_flag_set',b'\x4e\xb9'),(0x15ca0,'time_model_flag_clear',b'\x4e\xb9'),(0xf55c,'time_model_terrain_visible',b'\x4e\xb9'),(0xf56e,'time_model_terrain_hidden',b'\x4e\xb9'),(0xf584,'time_model_terrain_type',b'\x4e\xb9'),(0x21b14,'time_auto_dispatch',b'\x4e\xf9'),(0xfe1e,'time_pose_added',b'\x4e\xb9'),(0xfed2,'time_pose_removed',b'\x4e\xb9'),(0xe128,'time_model_default',b'\x4e\xb9'),(0xe150,'time_model_player',b'\x4e\xb9'),(0xe1a6,'time_model_variant',b'\x4e\xb9'),(0xdf3e,'time_model_color',b'\x4e\xb9'),(0xdf92,'time_model_polygon',b'\x4e\xb9'),(0x56c,'time_present_begin',b'\x4e\xf9'),(0xb16,'time_present_end',b'\x4e\xf9'),(0x2c55a,'time_present_capture',b'\x4e\xb9'),(0xeca,'time_compress_clock',b'\x4e\xb9'),(0x21dae,'time_compress_selector',b'\x4e\xb9'),(0x21dce,'time_camera_world_build',b'\x4e\xb9'),(0x16774,'time_camera_world_orbit',b'\x4e\xb9'),(0x16788,'time_camera_world_free',b'\x4e\xb9'),(0x3c06,'time_message_start',b'\x4e\xb9'),(0x3c7c,'time_message_shorten',b'\x4e\xb9'),(0x84e,'time_message_render',b'\x4e\xb9'),(0xab4,'time_message_clear',b'\x4e\xb9'),(0x3ce4,'time_rate_write',b'\x4e\xb9'),(0x21d28,'time_loop_gate',b'\x4e\xb9'),(0x21e7a,'time_loop_draw',b'\x4e\xb9'),(0x3d5e,'time_loop_clock',b'\x4e\xb9'),(0x21f60,'time_loop_exit',b'\x4e\xf9'),(0x21ba2,'time_pause_menu',b'\x4e\xb9'),(0x21c02,'time_pause_menu',b'\x4e\xb9'),(0x21c20,'time_pause_preferences',b'\x4e\xb9'),(0x21c82,'time_pause_controls',b'\x4e\xb9'),(0x21bf6,'time_pause_wait',b'\x4e\xb9'),(0x308b6,'time_input_observe_irq',b'\x4e\xb9'),(0x309c0,'time_keys_query',b'\x4e\xb9'),(0x309cc,'time_keys_pop',b'\x4e\xb9'),(0x2d35c,'time_mouse_delta',b'\x4e\xb9'),(0x1ecd0,'time_mouse_read',b'\x4e\xb9'),(0x1e8ec,'time_mouse_center',b'\x4e\xb9'),(0x1ebba,'time_mouse_camera_done',b'\x4e\xb9'),(0x1eb5c,'time_mouse_camera_x',b'\x4e\xb9'),(0x1eb70,'time_mouse_camera_y',b'\x4e\xb9'),(0x1eb8a,'time_mouse_camera_center',b'\x4e\xb9'),(0x2d412,'time_devices_vbl_end',b'\x4e\xb9'),(0x30a4e,'time_devices_joy',b'\x4e\xb9'),(0x30afc,'time_devices_fire',b'\x4e\xb9'),(0x1ecfe,'time_devices_joy_pointer',b'\x4e\xb9'),(0x1ece8,'time_devices_x',b'\x4e\xb9'),(0x1ecf2,'time_devices_y',b'\x4e\xb9'),(0x1edae,'time_devices_left',b'\x4e\xb9'),(0x1edec,'time_devices_right',b'\x4e\xb9')]:
 if not mask & 8192:continue
 expect=op+(slave+symbol(name)).to_bytes(4,'big')
 assert read(m['entry']['sim']+off,6)==expect,(hex(off),name)
 selected.append(hex(off))
if mask & 256:
 assert read(m['entry']['sim']+0xb06,2)==b'\x70\x01'
 selected.append('0xb06')
if mask & 512:
 for off,name in [(0xb08,'pace_flight'),(0x2d34e,'pace_vbl')]:
  assert read(m['entry']['sim']+off,6)==b'\x4e\xb9'+(slave+symbol(name)).to_bytes(4,'big')
  selected.append(hex(off))
if mask & 8192:assert read(m['entry']['sim']+0x21d2e,2)==b'\x4e\x71'
assert int.from_bytes(read(slave+symbol('perf_mask'),4),'big')==mask
result={'disabled_ranges':len(spans),'selected_ranges':selected,'passed':True,'sha256':m['slave_sha256']}
(a.capture/'byte-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
