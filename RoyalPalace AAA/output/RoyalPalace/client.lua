local RES=getThisResource()
local world, objects, models = nil, {}, {}
local palette={}
local baseTime, baseMinute, baseWeather, originalDimension
local function say(s,r) outputChatBox("#D7B878[Royal Palace] #FFFFFF"..s,r or localPlayer,215,184,120,true) end
local function readWorld()
 local f=fileOpen("client/data/world.json"); if not f then return nil end
 local s=fileRead(f,fileGetSize(f)); fileClose(f); return fromJSON(s)
end
local function install()
 world=readWorld(); if not world then say("تعذر تحميل بيانات القصر"); return end
 local txdByGroup={}
 for group,rec in pairs(world.txds or {}) do
  local t=engineLoadTXD(rec.path); if t then txdByGroup[group]=t else say("فشل تحميل خامة: "..group) end
 end
 local id=15000
 for name,m in pairs(world.models or {}) do
  if id>16000 then say("تجاوز حد معرّفات النماذج"); return end
  local ok=true
  for _,g in ipairs(m.txds or {}) do local t=txdByGroup[g]; if t then engineImportTXD(t,id) end end
  local d=engineLoadDFF(m.dff,id); if not d then ok=false; say("فشل DFF: "..name) else engineReplaceModel(d,id) end
  local c=engineLoadCOL(m.col); if c then engineReplaceCOL(c,id) else ok=false; say("فشل COL: "..name) end
  if ok then engineSetModelLODDistance(id,m.draw or 300); models[name]=id else engineRestoreModel(id) end
  id=id+1
 end
 objects=world.objects or {}; setTimer(spawnBatch,50,1,1); say("تحميل الأصول اكتمل؛ جارٍ إنشاء المشهد")
end
function spawnBatch(i)
 local stop=math.min(i+34,#objects)
 for n=i,stop do local q=objects[n]; local mid=models[q.model]
  if mid and q.pos then local o=createObject(mid,q.pos[1],q.pos[2],q.pos[3],q.rot and q.rot[1] or 0,q.rot and q.rot[2] or 0,q.rot and q.rot[3] or 0)
   if o then setElementDimension(o,world.dimension or 0); setElementDoubleSided(o,false); setObjectBreakable(o,false); palette[#palette+1]=o end
  end
 end
 if stop<#objects then setTimer(spawnBatch,20,1,stop+1) else say("القصر جاهز — "..#palette.." قطعة هندسية") end
end
local function destination(key)
 if not world then return end
 local ids={throne='3',library='21',bedroom='11',dining='6',balcony='16'}
 if key=='entrance' then key='gate' end
 local p=world.teleports[key]
 if ids[key] then local r=world.rooms[ids[key]]; p=r and r.spawn and {pos=r.spawn,rot=0} end
 if p and p.pos then setElementDimension(localPlayer,world.dimension or 0); setElementPosition(localPlayer,p.pos[1],p.pos[2],p.pos[3]+1); setElementRotation(localPlayer,0,0,p.rot or 0) end
end
local function day(night)
 if not baseTime then baseTime={getTime()}; baseMinute={getMinute()}; baseWeather=getWeather() end
 setTime(night and 0 or 12,night and 20 or 0); setWeather(night and 9 or 10)
 setSkyGradient(night and 5 or 165,night and 12 or 205,night and 22 or 235,night and 12 or 180,night and 20 or 210,night and 38 or 230)
 setTrafficLightState(night and "green" or "auto")
end
local isNight=false
addCommandHandler("palace",function()
 outputChatBox("#D7B878—— القصر الملكي ——",215,184,120,true)
 outputChatBox("#FFFFFF[1] المدخل  [2] قاعة العرش  [3] المكتبة  [4] غرفة النوم  [5] قاعة الطعام  [6] الشرفة",255,255,255,true)
 outputChatBox("[/palace day|night] لتغيير الإضاءة",255,255,255,true)
end)
addCommandHandler("showp",function() for _,o in ipairs(palette) do if isElement(o) then setElementAlpha(o,255) end end; say("المشهد ظاهر") end)
addCommandHandler("palacehide",function() for _,o in ipairs(palette) do if isElement(o) then setElementAlpha(o,0) end end; say("تم إخفاء القصر") end)
addCommandHandler("palace",function(_,arg)
 if arg=="day" then isNight=false; day(false) elseif arg=="night" then isNight=true; day(true) end
end)
for k,v in pairs({["1"]="entrance",["2"]="throne",["3"]="library",["4"]="bedroom",["5"]="dining",["6"]="showp"}) do bindKey(k,"down",function() if world then destination(v) end end) end
addEventHandler("onClientResourceStart",resourceRoot,function() originalDimension=getElementDimension(localPlayer); install() end)
addEventHandler("onClientResourceStop",resourceRoot,function()
 for _,o in ipairs(palette) do if isElement(o) then destroyElement(o) end end
 for id in pairs(models) do engineRestoreModel(id); engineRestoreCOL(id) end
 if isElement(localPlayer) and originalDimension then setElementDimension(localPlayer,originalDimension) end
 if baseTime then setTime(baseTime[1],baseMinute[1]); setWeather(baseWeather); setSkyGradient() end
end)
