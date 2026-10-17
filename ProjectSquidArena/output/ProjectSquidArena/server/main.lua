local WORLD
local function loadWorld()
 local p='data/world.json';if not fileExists(p) then outputDebugString('[ProjectSquidArena] missing '..p,1);return false end
 local f=fileOpen(p);if not f then return false end
 local s=fileRead(f,fileGetSize(f));fileClose(f);WORLD=fromJSON(s)
 if type(WORLD)~='table' or not WORLD.arenas or not WORLD.placements then outputDebugString('[ProjectSquidArena] invalid world manifest',1);WORLD=nil;return false end
 return true
end
function squidArenaWorld() return WORLD end
addEventHandler('onResourceStart',resourceRoot,function() if loadWorld() then outputDebugString('[ProjectSquidArena] world manifest loaded: '..#WORLD.placements..' placements') end end)
addEventHandler('onResourceStop',resourceRoot,function()
 for _,p in ipairs(getElementsByType('player')) do
  local old=getElementData(p,'squid:restore')
  if old then setElementDimension(p,old.dimension or 0);setElementInterior(p,old.interior or 0);setElementPosition(p,old.x or 0,old.y or 0,old.z or 5);setElementData(p,'squid:restore',false) end
 end
end)
