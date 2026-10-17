local matches={tug=nil,bridge=nil}
local aiTimer
local function msg(p,s,r,g,b) if isElement(p) then outputChatBox('#28d7ef[Squid Arena] #FFFFFF'..s,p,r or 230,g or 240,b or 245,true) end end
local function origin(arena) local a=SQUID_CONFIG.arenas[arena];return a.origin.x,a.origin.y,a.origin.z end
local function pos(arena,x,y,z) local ox,oy,oz=origin(arena);return ox+x,oy+y,oz+z end
local function setAt(p,arena,x,y,z)
 local X,Y,Z=pos(arena,x,y,z);setElementDimension(p,SQUID_CONFIG.arenas[arena].dimension);setElementInterior(p,0);setElementPosition(p,X,Y,Z);setElementRotation(p,0,0,0);setCameraTarget(p,p)
end
local function remember(p)
 if getElementData(p,'squid:restore') then return end
 local x,y,z=getElementPosition(p);setElementData(p,'squid:restore',{x=x,y=y,z=z,dimension=getElementDimension(p),interior=getElementInterior(p)},false)
end
local function spawnBot(arena,x,y,z,skin,rotation)
 local X,Y,Z=pos(arena,x,y,z);local ped=createPed(skin or 13,X,Y,Z,rotation or 0)
 if ped then setElementDimension(ped,SQUID_CONFIG.arenas[arena].dimension);setElementFrozen(ped,true);setPedAnimation(ped,'ped','IDLE_tired',-1,true,false,false,false);setElementData(ped,'squid:bot',true,false) end
 return ped
end
local function clearMatch(arena)
 local m=matches[arena];if not m then return end
 if isTimer(m.timer) then killTimer(m.timer) end
 if m.bots then for _,b in ipairs(m.bots) do if isElement(b) then destroyElement(b) end end end
 if m.player and isElement(m.player) then setElementData(m.player,'squid:match',false,false);triggerClientEvent(m.player,'squid:matchEnd',resourceRoot,arena) end
 matches[arena]=nil
end
local function finish(arena,won,reason)
 local m=matches[arena];if not m then return end
 if m.player and isElement(m.player) then
  msg(m.player,won and 'فزت على فريق الذكاء الاصطناعي! '..(reason or '') or 'خسرت الجولة. '..(reason or ''),won and 91 or 255,won and 220 or 100,won and 120 or 100)
  triggerClientEvent(m.player,'squid:result',resourceRoot,arena,won,reason or '')
  if arena=='bridge' then local X,Y,Z=pos(arena,0,won and 41 or -40,won and 1 or -20);setElementPosition(m.player,X,Y,Z) end
 end
 clearMatch(arena)
end
local function makeSafeSequence()
 local t={};for i=1,SQUID_CONFIG.arenas.bridge.steps do t[i]=math.random(1,2) end;return t
end
local function activePlayerMatch(p) for k,m in pairs(matches) do if m and m.player==p then return k end end end
local function startTug(p)
 if activePlayerMatch(p) then return msg(p,'أنت بالفعل داخل جولة؛ استخدم /squid leave أولاً.') end
 if matches.tug then return msg(p,'ساحة شد الحبل مشغولة حالياً؛ حاول لاحقاً.') end
 remember(p);local a=SQUID_CONFIG.arenas.tug;setAt(p,'tug',a.entry.x,a.entry.y,a.entry.z)
 local bots={};for i=1,SQUID_CONFIG.ai.tugTeamSize do bots[#bots+1]=spawnBot('tug',15,(-1.5+(i-1)*1.5),1.0,({9,13,15})[i],180) end
 local m={arena='tug',player=p,bots=bots,progress=0,pulls=0,lastPull=0,started=getTickCount()};matches.tug=m
 setElementData(p,'squid:match','tug',false);triggerClientEvent(p,'squid:matchStart',resourceRoot,'tug');triggerClientEvent(p,'squid:tugUpdate',resourceRoot,0)
 msg(p,'شد الحبل ضد 3 منافسين آليين. اضغط باستمرار على زر الفأرة الأيسر أو Space.');msg(p,'الفوز عندما تسحب العلامة إلى جهتك؛ فريق الذكاء الاصطناعي يسحب عكسك.')
 m.timer=setTimer(function()
   if matches.tug~=m or not isElement(p) then return end
   m.progress=math.max(-8,math.min(8,m.progress-(0.15+math.random()*0.18)))
   triggerClientEvent(p,'squid:tugUpdate',resourceRoot,m.progress)
   if m.progress<=-8 then finish('tug',false,'تغلب عليك الفريق الآلي.') elseif m.progress>=8 then finish('tug',true,'') end
   if getTickCount()-m.started>90000 then finish('tug',m.progress>0,'انتهى الوقت.') end
  end,1000,0)
end
local function startBridge(p)
 if activePlayerMatch(p) then return msg(p,'أنت بالفعل داخل جولة؛ استخدم /squid leave أولاً.') end
 if matches.bridge then return msg(p,'جسر الزجاج مشغول حالياً؛ حاول لاحقاً.') end
 remember(p);local a=SQUID_CONFIG.arenas.bridge;setAt(p,'bridge',a.entry.x,a.entry.y,a.entry.z)
 local bot=spawnBot('bridge',a.ai.x,a.ai.y,a.ai.z,14,0)
 local m={arena='bridge',player=p,bots={bot},sequence=makeSafeSequence(),step=1,aiStep=1,aiAlive=true,started=getTickCount(),lastChoice=0,hintStep=0,choiceDeadline=getTickCount()+15000};matches.bridge=m
 setElementData(p,'squid:match','bridge',false);triggerClientEvent(p,'squid:matchStart',resourceRoot,'bridge')
 msg(p,'جسر الزجاج: اختر اليسار أو اليمين بالأزرار A / D أو بالأمر /panel left|right.');msg(p,'اسأل رفيقك الآلي بالأمر /squid ai؛ نصيحته جيدة لكنها ليست مضمونة.')
 m.timer=setTimer(function()
   if matches.bridge~=m or not isElement(p) then return end
   if getTickCount()>m.choiceDeadline then finish('bridge',false,'انتهى وقت الاختيار.');return end
   if m.aiStep<=#m.sequence and math.random()<SQUID_CONFIG.ai.bridgeSkill then
    local lane=m.sequence[m.aiStep];m.aiStep=m.aiStep+1
    if isElement(bot) then local x=lane==1 and -1.25 or 1.25;local y=-32+(m.aiStep-2)*3.8;local X,Y,Z=pos('bridge',x,y,1.0);setElementFrozen(bot,false);setElementPosition(bot,X,Y,Z);setElementFrozen(bot,true) end
   elseif m.aiStep<=#m.sequence then
    if isElement(bot) then local X,Y,Z=pos('bridge',0,-39,-18);setElementFrozen(bot,false);setElementPosition(bot,X,Y,Z);setElementFrozen(bot,true) end
    m.aiStep=#m.sequence+1;m.aiAlive=false;msg(p,'رفيقك الآلي أخطأ وسقط! أسرع قبل أن تصل للنهاية.')
   end
   if m.aiAlive and m.aiStep==#m.sequence+1 then finish('bridge',false,'وصل المتسابق الآلي قبلك!');return end
   if m.aiStep>#m.sequence+1 then m.aiStep=#m.sequence+1 end
  end,2500,0)
end
addCommandHandler('squid',function(p,_,arg)
 if not isElement(p) then return end
 arg=(arg or 'help'):lower()
 if arg=='tug' then startTug(p)
 elseif arg=='bridge' then startBridge(p)
 elseif arg=='leave' then
  local found;for k,m in pairs(matches) do if m and m.player==p then found=k;break end end
  if found then clearMatch(found) end
  local old=getElementData(p,'squid:restore');if old then setElementDimension(p,old.dimension or 0);setElementInterior(p,old.interior or 0);setElementPosition(p,old.x,old.y,old.z);setElementData(p,'squid:restore',false);msg(p,'خرجت من الساحة.') end
 elseif arg=='ai' then
  local m=matches.bridge;if not m or m.player~=p then return msg(p,'ابدأ الجسر أولاً: /squid bridge') end
  if m.hintStep==m.step then return msg(p,'رفيقك أعطى نصيحته لهذه الخطوة بالفعل؛ عليك الاختيار الآن.') end
  m.hintStep=m.step;local real=m.sequence[m.step];local advice
  if math.random()<SQUID_CONFIG.ai.bridgeSkill then advice=real else advice=3-real end
  msg(p,'رفيقك الآلي ينصح: '..(advice==1 and 'اليسار' or 'اليمين')..' (ثقته ليست كاملة).')
 else
  msg(p,'الأوامر: /squid tug — شد الحبل ضد AI | /squid bridge — جسر زجاج ضد AI | /squid ai — نصيحة | /panel left|right | /squid leave')
 end
end)
local function choice(p,lane)
 local m=matches.bridge;if not m or m.player~=p then return msg(p,'ابدأ جولة الجسر أولاً.') end
 if getTickCount()-m.lastChoice<450 then return end;m.lastChoice=getTickCount()
 local step=m.step;if step>#m.sequence then return end
 local safe=m.sequence[step]
 triggerClientEvent(root,'squid:panelState',resourceRoot,step,safe)
 if lane~=safe then
  msg(p,'اللوح تحطم تحتك! نصيحة الذكاء الاصطناعي ليست ضماناً.')
  finish('bridge',false,'اخترت اللوح الخطأ.')
  return
 end
 m.step=step+1;m.choiceDeadline=getTickCount()+15000;local x=lane==1 and -1.25 or 1.25;local y=-32+(step-1)*3.8;setAt(p,'bridge',x,y,1.1)
 msg(p,'لوح آمن! '..math.min(step,#m.sequence)..' / '..#m.sequence)
 triggerClientEvent(p,'squid:bridgeStep',resourceRoot,step,lane,m.aiStep)
 if m.step>#m.sequence then finish('bridge',true,'عبرت الجسر قبل الخصم الآلي.') end
end
addCommandHandler('panel',function(p,_,side) side=(side or ''):lower();if side=='left' then choice(p,1) elseif side=='right' then choice(p,2) else msg(p,'اكتب /panel left أو /panel right') end end)
addEvent('squid:pull',true);addEventHandler('squid:pull',resourceRoot,function()
 local p=client;local m=matches.tug;if not isElement(p) or not m or m.player~=p then return end
 local now=getTickCount();if now-m.lastPull<220 then return end;m.lastPull=now
 m.progress=math.min(8,m.progress+0.28);m.pulls=m.pulls+1
 triggerClientEvent(p,'squid:tugUpdate',resourceRoot,m.progress)
 if m.progress>=8 then finish('tug',true,'') end
end)
addEvent('squid:bridgeChoice',true);addEventHandler('squid:bridgeChoice',resourceRoot,function(lane) if client and (lane==1 or lane==2) then choice(client,lane) end end)
addEventHandler('onPlayerQuit',root,function()for k,m in pairs(matches) do if m and m.player==source then clearMatch(k) end end end)
addEventHandler('onResourceStop',resourceRoot,function()for k in pairs(matches) do clearMatch(k) end end)
addEventHandler('onPlayerWasted',root,function()for k,m in pairs(matches) do if m and m.player==source then finish(k,false,'تم إقصاؤك.') end end end)
