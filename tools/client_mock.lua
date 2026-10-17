-- Test-only fake handles and API calls. No window, GPU, images or game renderer.
__ids={};__nextID=3221;__assetCalls={};__serverEvents={};__fail=false;__surface=28;__drawCalls=0;__nativeTXDs={}
-- Do not seed production globals. IDs are recycled just as in the real allocator.
local function call(n)__assetCalls[#__assetCalls+1]=n end
function engineRequestModel(kind,parent)
 assert(kind=="object" and parent==1337);local id=3222;while __ids[id] do id=id+1 end
 __nextID=id;__ids[id]={txdID=77};call("request");return id
end
function engineGetModelTXDID(id)assert(__ids[id]);return __ids[id].txdID end
function engineLoadCOL(path)call("COL");if __fail=="COL" then return false end;return _element("col")end
function engineReplaceCOL(c,id)assert(__ids[id]);call("replaceCOL");if __fail=="replaceCOL" then return false end;__ids[id].col=c;return true end
function engineLoadTXD(path,filtering)
 call("TXD");assert(filtering==false,"preserve exported mipmap/filter settings")
 if __fail=="TXD" then return false end
 local t=_element("txd");t.path=path;t.imported={};return t
end
function engineImportTXD(t,id)
 assert(__ids[id] and isElement(t));call("importTXD")
 if __fail=="importTXD" or t.imported[id] then return false end
 -- CRenderWareSA::ModelInfoTXDAddTextures remembers IDs after engineFreeModel.
 t.imported[id]=true;local slot=__ids[id].txdID
 __nativeTXDs[slot]=__nativeTXDs[slot] or {};__nativeTXDs[slot][t]=true;return true
end
function engineLoadDFF(path)call("DFF");if __fail=="DFF" then return false end;local d=_element("dff");d.path=path;return d end
function engineReplaceModel(d,id)
 assert(__ids[id]);call("replaceDFF");if __fail=="replaceDFF" then return false end
 local dictionaries=__nativeTXDs[__ids[id].txdID];assert(dictionaries and next(dictionaries),"DFF before available shared TXD")
 for _,model in pairs(RFScene.data.models) do
  if model.dff==d.path then
   for _,g in ipairs(model.txds) do
    local wanted=RFScene.data.txds[g].path;local found=false
    for t in pairs(dictionaries) do if isElement(t) and t.path==wanted then found=true end end
    assert(found,"DFF texture group "..g.." is not loaded in the inherited TXD slot")
   end
   break
  end
 end
 __ids[id].dff=d;return true
end
function engineSetModelLODDistance(id,distance,extended)assert(__ids[id] and extended==true);return true end
function engineRestoreModel(id)
 call("restoreModel");if not __ids[id] or not __ids[id].dff then return false end
 __ids[id].dff=nil;return true
end
function engineRestoreCOL(id)
 call("restoreCOL");if not __ids[id] or not __ids[id].col then return false end
 __ids[id].col=nil;return true
end
function engineFreeModel(id)
 for _,o in ipairs(getElementsByType("object")) do assert(o.model~=id,"freed model while an object owns it") end
 assert(__ids[id]);__ids[id]=nil;return true
end
local nativeDestroy=destroyElement
function destroyElement(e)
 if isElement(e) and getElementType(e)=="txd" then
  for id in pairs(e.imported or {}) do assert(__ids[id],"TXD import target freed before its dictionary") end
  for slot,dictionaries in pairs(__nativeTXDs) do
   dictionaries[e]=nil;if not next(dictionaries) then __nativeTXDs[slot]=nil end
  end
 end
 return nativeDestroy(e)
end
function createObject(id,x,y,z,rx,ry,rz,low)
 assert(__ids[id] and __ids[id].dff);local o=_element("object",x,y,z);o.rx=rx;o.ry=ry;o.rz=rz;o.model=id;o.low=low;o.collisions=true;return o
end
function setObjectScale(o,s)o.scale=s;return true end
function setElementCollisionsEnabled(o,v)o.collisions=v;return true end
function setElementStreamable(o,v)o.streamable=v;return true end
function setLowLODElement(hi,lo)assert(not hi.low and lo.low);hi.lod=lo;return true end
function isElementStreamedIn(o)return isElement(o)end
function createWater(...)local a={...};assert(a[#a]==false,"oasis water must be visible, not bShallow");return _element("water")end
function dxCreateTexture(path)if __fail=="texture" or not fileExists(path) then return false end;return _element("texture")end
function dxCreateShader(path)
 assert(fileExists(path));if __fail=="shader" then return false end
 local f=fileOpen(path);local text=fileRead(f,fileGetSize(f));fileClose(f)
 local shader=_element("shader")
 shader.baseTextureMapped=text:find('textureState%s*=%s*"0,Texture"')~=nil
 shader.nativeVertexPipeline=not text:find('VertexShader%s*=%s*compile')
 shader.technique="CityNativePixels"
 return shader,shader.technique
end
function dxSetShaderValue(s,name,...)
 assert(isElement(s));if __uniformFail==name then return false end
 if s.technique=="Basic" and (name=="gDetail" or name=="gDetailScale" or name=="gDetailStrength" or name=="gStorm") then return false end
 s[name]={...};return true
end
function engineApplyShaderToWorldTexture(s,pattern)
 if __bindFail==pattern then return false end
 s.patterns=s.patterns or {};s.patterns[pattern]=true;return true
end
function engineRemoveShaderFromWorldTexture(s,pattern)
 if not s.patterns or not s.patterns[pattern] then return false end
 s.patterns[pattern]=nil;return true
end
function dxDrawMaterialLine3D(...)__drawCalls=__drawCalls+1;return true end
function dxDrawText()return true end
function tocolor(r,g,b,a)return a or 255 end
function playSound(path)assert(fileExists(path));return _element("sound")end
function stopSound(s)return destroyElement(s)end
function setSoundVolume(s,v)s.volume=v;return true end
local enabled={}
function isControlEnabled(name)return enabled[name]~=false end
function toggleControl(name,v)enabled[name]=v;return true end
function getPedControlState(p,name)return p.controls and p.controls[name] or false end
function fadeCamera(value)__fade=value;return true end
function setCameraTarget(p)__camera=p;return true end
function getCameraMatrix()local x,y,z=getElementPosition(localPlayer);return x,y-8,z+4,x,y,z end
function getElementMatrix(e)
 local x,y,z=getElementPosition(e);local a=math.rad(e.rz or 0);local c,s=math.cos(a),math.sin(a)
 return {{c,s,0,0},{-s,c,0,0},{0,0,1,0},{x,y,z,1}}
end
function getVehicleComponents()return {wheel_lf_dummy=true,wheel_rf_dummy=true,wheel_lb_dummy=true,wheel_rb_dummy=true}end
function getVehicleComponentPosition(v,name,base)
 local x,y,z=getElementPosition(v);return x+(name:find("_l") and -.85 or .85),y+(name:find("f_") and 1.2 or -1.2),z-.23
end
function getElementBoundingBox()return -1,-2,-.7,1,2,1.1 end
function isVehicleOnGround(v)return not v.airborne end
function isPedOnGround(p)return not p.vehicle end
function processLineOfSight(x,y,z,x2,y2,z2,...)
 -- test model: the floor is at __floorZ (default: the travel target) and belongs to the nearest streamed fortress object
 local fz=__floorZ or (z+z2)/2
 if fz>z or fz<z2 then return false end
 local best,bd=false,1e18
 for e in pairs(RFScene.byElement) do if isElement(e) then local d=(e.x-x)^2+(e.y-y)^2;if d<bd then best,bd=e,d end end end
 if not best or __noFloor then return false end
 return true,x,y,fz,best,0,0,1,0,1
end
function triggerServerEvent(name,source,...)__serverEvents[#__serverEvents+1]={name=name,args={...}};return true end
function guiGetScreenSize()return 1280,720 end
__environment={weather=3,time={11,23},minute=1000,sky={1,2,3,4,5,6},sun={11,12,13,14,15,16},sunSize=1.2,far=900,fog=300,wind={.1,.2,0},clouds=true,rain=.2,heat={1,2,3,4,5,6,7,8,9},waterColor={3,4,5,6},wave=.4}
local pairsToSet={Weather="weather",Time="time",MinuteDuration="minute",SkyGradient="sky",SunColor="sun",SunSize="sunSize",FarClipDistance="far",FogDistance="fog",WindVelocity="wind",CloudsEnabled="clouds",RainLevel="rain",HeatHaze="heat",WaterColor="waterColor",WaveHeight="wave"}
for suffix,key in pairs(pairsToSet) do
 local k=key
 _G["get"..suffix]=function()local v=__environment[k];if type(v)=="table" then return unpack(v) end;return v end
 _G["set"..suffix]=function(...)local a={...};__environment[k]=#a==1 and a[1] or a;return true end
end

-- Native color grade API model, including original-vs-custom restoration.
__environment.filter={20,15,9,60,6,9,12,20};__environment.originalFilter={28,21,12,40,9,12,18,35};__environment.filterCustom=true
function getColorFilter(original)assert(type(original)=="boolean");return unpack(original and __environment.originalFilter or __environment.filter)end
function setColorFilter(...)local a={...};assert(#a==8);for _,v in ipairs(a) do assert(v>=0 and v<=255) end;__environment.filter=a;__environment.filterCustom=true;return true end
function resetColorFilter()__environment.filter={unpack(__environment.originalFilter)};__environment.filterCustom=false;return true end

function createMarker(x,y,z,kind,size,r,g,b,a)local e=_element("marker",x,y,z);e.color={r,g,b,a};return e end
function setMarkerColor(e,r,g,b,a)e.color={r,g,b,a};return true end
function getVehicleOverrideLights(v)return v.lights or 0 end

function bindKey(key,state,fn)__keys=__keys or {};__keys[key]=fn;return true end
function isCursorShowing()return false end
function isChatBoxInputActive()return false end
function getScreenFromWorldPosition()return 100,100 end
function dxDrawLine3D()return true end
__moves={}
function moveObject(o,t,x,y,z,rx,ry,rz,easing)__moves[#__moves+1]={o=o,t=t,x=x,y=y,z=z,rx=rx,ry=ry,rz=rz};return true end
function stopObject(o)return true end
