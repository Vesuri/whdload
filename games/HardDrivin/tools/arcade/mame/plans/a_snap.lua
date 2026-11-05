-- Attract mode: snap every 0.5 s from 100 to 150 s after power-on.
local e = {}
for i = 0, 99 do e[#e + 1] = {t=100 + i * 0.5, snap=true} end
e[#e + 1] = {t=150.2, exit=true}
return { events = e }
