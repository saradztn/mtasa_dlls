local W,modelIds,objects,panelObjects={}, {}, {}, {}
local screen, shaders={},{};local quality='high';local match=nil;local tugRope;local loading=false;local loadingCount=0;local safeMark={};local lastClick=0
local function say(s) outputChatBox('#25D9F0[Squid Arena] #FFFFFF'..s,255,255,255,true) end
local function loadWorld()
 if not fileExists('data/world.json') then outputDebugString('[SquidArena] data/world.json missing',1);return false end
 local f=fileOpen('data/world.json');if not f then return false end
 local text=fileRead(f,fileGetSize(f));fileClose(f);W=fromJSON(text)
 if type(W)~='table' or not W.models or not W.placements then return false end
 return true
end
local function modelLoadQueue()
 if not W or loading then return end;loading=true
 local names={};for n in pairs(W.models) do names[#names+1]=n end;table.sort(names)
 local ids={};for i,n in ipairs(names) do local id=(W.model_base or 15000)+i-1;modelIds[n]=id;ids[#ids+1]=id end
 local txd=engineLoadTXD('textures/squid_arena.txd',false)
 if not txd then outputDebugString('[SquidArena] TXD load failed; custom surface appearance unavailable',1) end
 local index=1
 local function batch()
  local limit=math.min(index+7,#names)
  for i=index,limit do
   local n=names[i];local id=modelIds[n];if txd then engineImportTXD(txd,id) end
   local d=engineLoadDFF(W.models[n].dff,id)
   local c=engineLoadCOL(W.models[n].col)
   if not d or not c then outputDebugString('[SquidArena] asset load failure: '..n,1)
   else
    local ok=engineReplaceModel(d,id);local cok=engineReplaceCOL(c,id)
    if ok==false or cok==false then outputDebugString('[SquidArena] model replacement failed: '..n,1) end
    engineSetModelLODDistance(id,350)
   end
  end
  index=limit+1
  if index<=#names then setTimer(batch,30,1) else loading=false;loadingCount=#names;createScene() end
 end
 batch()
end
function createScene()
 if not W then return end
 local list=W.placements;local i=1
 local function batch()
  local stop=math.min(i+23,#list)
  for k=i,stop do
   local q=list[k];local ar=W.arenas[q.arena];local id=modelIds[q.model]
   if ar and id then
    local p=q.pos;local o=createObject(id,ar.origin[1]+p[1],ar.origin[2]+p[2],ar.origin[3]+p[3],q.rot[1],q.rot[2],q.rot[3],true)
    if o then
     setElementDimension(o,ar.dimension);setElementInterior(o,0);setElementDoubleSided(o,false);setObjectBreakable(o,false)
     objects[#objects+1]=o
     if q.model=='rope' and q.arena=='tug' then tugRope=o end
     if q.panel then panelObjects[q.panel+1]=panelObjects[q.panel+1] or {};panelObjects[q.panel+1][q.lane==-1 and 1 or 2]=o;setElementCollisionsEnabled(o,false) end
    else outputDebugString('[SquidArena] createObject failed: '..q.model,1) end
   end
  end
  i=stop+1;if i<=#list then setTimer(batch,15,1) else say('تم تحميل ساحتي اللعب والأصول؛ '..#objects..' قطعة هندسية. اكتب /squid للبدء.') end
 end
 batch()
end
local function makeEffects()
 local w,h=guiGetScreenSize();local scale=quality=='low' and 2 or quality=='high' and 1.5 or 1
 screen=dxCreateScreenSource(math.max(320,math.floor(w/scale)),math.max(180,math.floor(h/scale)))
 local definitions={{'wet_surface.fx','sq_floor','wet',.9,.78},{'wet_surface.fx','sq_steel','wet',.82,.48},{'wet_surface.fx','sq_steel2','wet',.7,.56},{'wet_surface.fx','sq_concrete','wet',.65,.20},{'glass.fx','sq_glass','glass',.38,.72},{'emissive.fx','sq_cyan','emissive',1,0},{'emissive.fx','sq_magenta','emissive',1,0}}
 for _,v in ipairs(definitions) do
  local sh,tech=dxCreateShader('shaders/'..v[1],0,0,false,'world')
  if sh then
   shaders[#shaders+1]=sh
   dxSetShaderValue(sh,'gQuality',quality=='low' and 0 or quality=='cinematic' and 2 or 1)
   if screen and v[3]~='emissive' then dxSetShaderValue(sh,'gScreen',screen) end
   if v[3]=='wet' then dxSetShaderValue(sh,'gWetness',SQUID_CONFIG.defaults.wetness*v[4]);dxSetShaderValue(sh,'gReflect',SQUID_CONFIG.defaults.reflection*v[5])
   elseif v[3]=='glass' then dxSetShaderValue(sh,'gAlpha',v[4]);dxSetShaderValue(sh,'gReflect',v[5]) end
   if not engineApplyShaderToWorldTexture(sh,v[2]) then outputDebugString('[SquidArena] shader texture target not found: '..v[2],2) end
  else outputDebugString('[SquidArena] shader fallback for '..v[1]..' (shader creation failed)',2) end
 end
end
addEventHandler('onClientPreRender',root,function()
 if screen and isElement(screen) then local d=getElementDimension(localPlayer);if d==SQUID_CONFIG.arenas.tug.dimension or d==SQUID_CONFIG.arenas.bridge.dimension then dxUpdateScreenSource(screen,true) end end
end)
local function beginGame(arena)match=arena;if arena=='bridge' then safeMark={} end;say(arena=='tug' and 'الجولة بدأت — اسحب بالحبل!' or 'الجولة بدأت — اختر طريقك بحذر.') end
local function endGame(arena)if match==arena then match=nil end;for _,row in pairs(panelObjects) do for _,o in pairs(row) do if isElement(o) then setElementCollisionsEnabled(o,true) end end end end
addEvent('squid:matchStart',true);addEventHandler('squid:matchStart',resourceRoot,function(arena)beginGame(arena)end)
addEvent('squid:matchEnd',true);addEventHandler('squid:matchEnd',resourceRoot,function(arena)endGame(arena)end)
addEvent('squid:result',true);addEventHandler('squid:result',resourceRoot,function(arena,won,reason)if match==arena then match=nil end;outputChatBox(won and '#49E099[Squid Arena] فوز!' or '#FF5577[Squid Arena] إقصاء!',255,255,255,true)end)
addEvent('squid:tugUpdate',true);addEventHandler('squid:tugUpdate',resourceRoot,function(progress)
 if isElement(tugRope) and W then local ar=W.arenas.tug;local p=tugRope;local _,y,z=getElementPosition(p);local base=ar.origin[1];setElementPosition(p,base+math.max(-8,math.min(8,progress))*0.40,y,z) end
end)
addEvent('squid:panelState',true);addEventHandler('squid:panelState',resourceRoot,function(step,safe)
 safeMark[step]=safe;local row=panelObjects[step];if row then for lane,o in pairs(row) do if isElement(o) then setElementCollisionsEnabled(o,lane==safe) end end end
end)
addEvent('squid:bridgeStep',true);addEventHandler('squid:bridgeStep',resourceRoot,function(step,lane,aiStep)if match=='bridge' then safeMark[step]=lane end end)
addEventHandler('onClientClick',root,function(button,state)
 if button=='left' and state=='down' and match=='tug' then local now=getTickCount();if now-lastClick>170 then lastClick=now;triggerServerEvent('squid:pull',resourceRoot) end end
end)
addEventHandler('onClientKey',root,function(key,pressed)
 if not pressed then return end
 if match=='tug' and key=='space' then local now=getTickCount();if now-lastClick>170 then lastClick=now;triggerServerEvent('squid:pull',resourceRoot) end
 elseif match=='bridge' then
  if key=='a' or key=='arrow_l' then triggerServerEvent('squid:bridgeChoice',resourceRoot,1)
  elseif key=='d' or key=='arrow_r' then triggerServerEvent('squid:bridgeChoice',resourceRoot,2) end
 end
end)
local function clearEffects()
 for _,s in ipairs(shaders) do if isElement(s) then destroyElement(s) end end;shaders={}
 if screen and isElement(screen) then destroyElement(screen) end;screen=nil
end
addCommandHandler('squidfx',function(_,preset)
 preset=(preset or 'high'):lower();if preset~='low' and preset~='high' and preset~='cinematic' then return say('الجودة: /squidfx low | high | cinematic') end
 quality=preset;clearEffects();makeEffects();say('جودة المؤثرات: '..preset)
end)
addEventHandler('onClientRender',root,function()
 if match=='tug' and (getKeyState('mouse1') or getKeyState('space')) then local now=getTickCount();if now-lastClick>260 then lastClick=now;triggerServerEvent('squid:pull',resourceRoot) end end
 if match=='tug' then
  dxDrawRectangle(0,30,dxGetTextWidth('S Q U I D  /  T U G   —   hold left click or SPACE',1.15,'default-bold')+34,34,tocolor(3,10,18,205))
  dxDrawText('S Q U I D  /  T U G   —   Hold left click or SPACE',12,36,700,60,tocolor(76,224,244,245),1.0,'default-bold','left','top',false,false,false,true)
 elseif match=='bridge' then
  dxDrawRectangle(0,30,590,54,tocolor(3,10,18,220));dxDrawText('GLASS BRIDGE  |  A: LEFT        D: RIGHT',12,35,575,56,tocolor(230,243,250,255),1.05,'default-bold','left','top',false,false,false,true)
  dxDrawText('Use /squid ai for a clue — it can be wrong.',12,58,575,82,tocolor(38,218,238,230),.88,'default','left','top',false,false,false,true)
 end
 if loading then dxDrawText('SQUID ARENA  •  loading assets',0,4,dxGetScreenSize(),32,tocolor(60,226,244,245),1.0,'default-bold','center','center') end
end)
addEventHandler('onClientResourceStart',resourceRoot,function()
 if loadWorld() then modelLoadQueue();makeEffects() else outputDebugString('[SquidArena] Could not read world manifest.',1) end
end)
addEventHandler('onClientResourceStop',resourceRoot,function()
 for _,o in ipairs(objects) do if isElement(o) then destroyElement(o) end end
 for _,s in ipairs(shaders) do if isElement(s) then destroyElement(s) end end
 if isElement(screen) then destroyElement(screen) end
 for _,id in pairs(modelIds) do engineRestoreModel(id);engineRestoreCOL(id) end
end)
