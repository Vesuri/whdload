-- Attract mode's second demo after the loop: log the playback pose at $FF8404
-- (X, Y, Z longs at 40 per foot, Y up; matrix column 2 forward) every 1/60 s
-- from HD_FROM to HD_TO seconds into pose.txt.
local m = manager.machine
local main = m.devices[":mainpcb:maincpu"].spaces["program"]
local from, to = tonumber(os.getenv("HD_FROM") or "113"), tonumber(os.getenv("HD_TO") or "170")
local f = io.open(os.getenv("HD_RUN") .. "/pose.txt", "w")
local function s16(a) local w = main:read_u16(a); if w >= 32768 then w = w - 65536 end; return w end
local function s32(a) local v = main:read_u32(a); if v >= 2147483648 then v = v - 4294967296 end; return v end
local function log()
  f:write(string.format("%.4f %d %d %d %d %d %d\n", m.time:as_double(), s32(0xff8404), s32(0xff8408),
    s32(0xff840c), s16(0xff8418), s16(0xff841e), s16(0xff8424)))
  f:flush()
end
local e = {}
for i = 0, math.floor((to - from) * 60) do e[#e + 1] = {t=from + i / 60, call=log, snap=(i % 120 == 0)} end
e[#e + 1] = {t=to + 0.1, exit=true}
return { events = e }
