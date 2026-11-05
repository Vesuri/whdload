-- Attract mode from power-on, no coin: log the MSP results and snap every 2 s.
local e = { {t=1, log=true} }
for i = 1, 120 do e[#e+1] = {t=i * 2, snap=true} end
e[#e+1] = {t=241, exit=true}
return { events = e }
