-- Created by: Arena.ai Agent Mode (AI) - headless MTA:SA API stub used by mta_lua_test.py (runs the real client.lua / server.lua)
math.atan2 = math.atan2 or function(y, x) return math.atan(y, x) end   -- MTA runs Lua 5.1
T = { now = 0, timers = {}, elems = {}, chat = {}, log = {}, hour = 12, files = {}, sounds_played = {}, nextModel = 20000, models = {}, freed = {}, anim = {}, keys = {}, draws = 0 }
local function newElem(kind, p) p = p or {} p.kind = kind p.alive = true T.elems[#T.elems + 1] = p return p end
root = newElem("root"); resourceRoot = newElem("resourceRoot"); localPlayer = newElem("player", { x = 100, y = 200, z = 20, rz = 90, vx = 0, vy = 0, vz = 0 })
local sides = {}
local function makeSide(name)
    local env = setmetatable({ side = name, handlers = {}, cmds = {} }, { __index = _G })
    sides[name] = env
    env.addEvent = function() return true end
    env.addEventHandler = function(ev, el, fn) env.handlers[ev] = env.handlers[ev] or {} table.insert(env.handlers[ev], { el = el, fn = fn }) return true end
    env.removeEventHandler = function(ev, el, fn)
        local l = env.handlers[ev] or {}
        for i = #l, 1, -1 do if l[i].fn == fn then table.remove(l, i) return true end end
        return false
    end
    env.addCommandHandler = function(n, fn) env.cmds[n] = fn end
    return env
end
local C, Sv = makeSide("client"), makeSide("server")
function T.fire(sd, ev, ...) for _, h in ipairs({ table.unpack(sd.handlers[ev] or {}) }) do h.fn(...) end end
-- shared element api -------------------------------------------------------------------------------------------
local function both(name, fn) C[name] = fn Sv[name] = fn end
both("isElement", function(e) return type(e) == "table" and e.alive == true end)
both("destroyElement", function(e) if type(e) == "table" then e.alive = false end return true end)
both("getElementPosition", function(e) return e.x, e.y, e.z end)
both("setElementPosition", function(e, x, y, z) e.x, e.y, e.z = x, y, z return true end)
both("getElementRotation", function(e) return e.rx or 0, e.ry or 0, e.rz or 0 end)
both("setElementRotation", function(e, rx, ry, rz) e.rx, e.ry, e.rz = rx, ry, rz return true end)
both("setElementFrozen", function(e, f) e.frozen = f return true end)
both("getElementVelocity", function(e) return e.vx or 0, e.vy or 0, e.vz or 0 end)
both("isPedInVehicle", function() return false end)
both("isPedDead", function() return false end)
both("setTimer", function(fn, ms, n) local t = { fn = fn, ms = ms, n = n, nxt = T.now + ms, alive = true } T.timers[#T.timers + 1] = t return t end)
both("killTimer", function(t) t.alive = false return true end)
both("isTimer", function(t) return type(t) == "table" and t.alive == true and t.fn ~= nil end)
both("getTickCount", function() return T.now end)
both("getTime", function() return math.floor(T.hour), math.floor((T.hour % 1) * 60) end)
both("outputDebugString", function(m) T.log[#T.log + 1] = "dbg:" .. m end)
both("tocolor", function(r, g, b, a) return 0 end)
function T.advance(ms)
    local stop = T.now + ms
    while true do
        local best
        for _, t in ipairs(T.timers) do if t.alive and t.nxt <= stop and (not best or t.nxt < best.nxt) then best = t end end
        if not best then break end
        T.now = best.nxt
        if best.n == 1 then best.alive = false else best.nxt = best.nxt + best.ms end
        best.fn()
    end
    T.now = stop
end
function T.frame(ms) T.advance(ms) T.fire(C, "onClientRender") end
function T.count(kind, alive_only) local n = 0 for _, e in ipairs(T.elems) do if e.kind == kind and (e.alive or not alive_only) then n = n + 1 end end return n end
function T.alive(kind) local n = 0 for _, e in ipairs(T.elems) do if e.kind == kind and e.alive then n = n + 1 end end return n end
-- client only ----------------------------------------------------------------------------------------------------
C.localPlayer, C.root, C.resourceRoot = localPlayer, root, resourceRoot
C.createObject = function(m, x, y, z, rx, ry, rz) return newElem("object", { model = m, x = x, y = y, z = z, rx = rx, ry = ry, rz = rz }) end
C.setObjectBreakable = function() return true end
C.moveObject = function(o, ms, x, y, z, rx, ry, rz) T.log[#T.log + 1] = "move:" .. o.model .. ":" .. string.format("%.0f", rz) o.rz = (o.rz or 0) + rz return true end
C.createWater = function(...) return newElem("water", { args = { ... } }) end
C.createEffect = function(...) return newElem("effect") end
C.createBlip = function(...) return newElem("blip") end
C.createLight = function(t, x, y, z) return newElem("light", { x = x, y = y, z = z }) end
C.playSound3D = function(f, x, y, z, loop) T.sounds_played[f] = (T.sounds_played[f] or 0) + 1 return newElem("sound", { file = f, loop = loop, vol = 1, x = x, y = y, z = z }) end
C.playSound = function(f, loop) T.sounds_played[f] = (T.sounds_played[f] or 0) + 1 return newElem("sound", { file = f, loop = loop, vol = 1 }) end
C.setSoundVolume = function(s, v) s.vol = v return true end
C.setSoundMinDistance = function() return true end
C.setSoundMaxDistance = function() return true end
C.setSoundSpeed = function() return true end
C.engineRequestModel = function(t, parent)
    if T.maxModels and #T.models >= T.maxModels then return false end
    T.nextModel = T.nextModel + 1 T.models[#T.models + 1] = T.nextModel return T.nextModel
end
C.engineFreeModel = function(id) T.freed[#T.freed + 1] = id return true end
local function loader(kind) return function(path) if not T.files[path] then return false end return newElem(kind, { path = path }) end end
C.engineLoadTXD, C.engineLoadDFF, C.engineLoadCOL = loader("txd"), loader("dff"), loader("col")
C.engineImportTXD = function() return true end
C.engineReplaceCOL = function() return true end
C.engineReplaceModel = function(d, id, alpha) T.replaced = (T.replaced or 0) + 1 return true end
C.engineSetModelLODDistance = function() return true end
C.dxCreateShader = function(f) if not T.files[f] then return false end return newElem("shader") end
C.engineApplyShaderToWorldTexture = function() return true end
C.engineRemoveShaderFromWorldTexture = function() return true end
C.dxDrawRectangle = function() T.draws = T.draws + 1 end
C.dxDrawText = function() T.draws = T.draws + 1 end
C.guiGetScreenSize = function() return 1920, 1080 end
C.bindKey = function(k, st, fn) T.keys[k] = fn end
C.unbindKey = function(k, st, fn) T.keys[k] = nil end
C.outputChatBox = function(m) T.chat[#T.chat + 1] = m end
C.triggerServerEvent = function(ev, src, ...) Sv.client = localPlayer T.fire(Sv, ev, ...) Sv.client = nil end
-- server only ----------------------------------------------------------------------------------------------------
Sv.root, Sv.resourceRoot = root, resourceRoot
Sv.outputChatBox = function(m, p) T.chat[#T.chat + 1] = "S:" .. m end
Sv.triggerClientEvent = function(target, ev, src, ...) T.log[#T.log + 1] = "toClient:" .. ev T.fire(C, ev, ...) end
Sv.setPedAnimation = function(p, block, anim) p.anim = block and (block .. "/" .. anim) or nil T.anim[#T.anim + 1] = p.anim or "none" return true end
Sv.setPedRotation = function(p, r) p.rz = r return true end
Sv.getDistanceBetweenPoints3D = function(a, b, c, d, e, f) return math.sqrt((a - d) ^ 2 + (b - e) ^ 2 + (c - f) ^ 2) end
Sv.getPlayerAccount = function() return "acc" end
Sv.isGuestAccount = function() return false end
Sv.getAccountName = function() return "tester" end
Sv.isObjectInACLGroup = function() return true end
Sv.aclGetGroup = function() return "g" end
C.getElementsByType = function(t, r, streamed) if t == "player" then return { localPlayer } end return {} end
function T.load(sd, chunkname, src)
    local fn, err = load(src, chunkname, "t", sides[sd])
    if not fn then error(err) end
    return fn()
end
function T.cmd(sd, name, ...) sides[sd].cmds[name](localPlayer, name, ...) end
function T.fireC(ev, ...) T.fire(C, ev, ...) end
function T.fireS(ev, ...) Sv.client = localPlayer T.fire(Sv, ev, ...) Sv.client = nil end
function T.handlerCount(ev) return #(C.handlers[ev] or {}) end
function T.liveTimers() local n = 0 for _, t in ipairs(T.timers) do if t.alive then n = n + 1 end end return n end
function T.light() local l = {} for _, e in ipairs(T.elems) do if e.kind == "light" and e.alive then l[#l + 1] = e end end return l end
function T.sound(file) local l = {} for _, e in ipairs(T.elems) do if e.kind == "sound" and e.alive and e.file:find(file, 1, true) then l[#l + 1] = e end end return l end
function T.objectsByModel(m) local l = {} for _, e in ipairs(T.elems) do if e.kind == "object" and e.alive and e.model == m then l[#l + 1] = e end end return l end
function T.key(k) if T.keys[k] then T.keys[k]() end end
function T.setPlayer(x, y, z, vx, vy) localPlayer.x, localPlayer.y, localPlayer.z, localPlayer.vx, localPlayer.vy = x, y, z, vx or 0, vy or 0 end
T.sides = sides
