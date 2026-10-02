-- Created by: Arena.ai Agent Mode (AI) - headless MTA:SA server stub + scenario test for zombies.lua (runs the REAL zombies.lua and zombie_nodes.lua)
math.atan2 = math.atan2 or function(y, x) return math.atan(y, x) end
local RES = ...
math.randomseed(tonumber(os.getenv("ZSEED")) or 4242)            -- resource directory
local E = setmetatable({}, { __index = _G })
local now, timers, elems, handlers, cmds, dbg, chat = 0, {}, {}, {}, {}, {}, {}
local fails, checks = 0, 0
local function check(c, msg) checks = checks + 1 if c then print("  [PASS] " .. msg) else fails = fails + 1 print("  [FAIL] " .. msg) end end

local function new(kind, p) p = p or {} p.kind, p.alive = kind, true elems[#elems + 1] = p return p end
E.root = new("root"); E.resourceRoot = new("resourceRoot")
local P = new("player", { x = 0, y = 0, z = 900, hp = 100, armor = 0, dead = false, move = "stand", dim = 0 })
local players = { P }

E.addEvent = function() return true end
E.addEventHandler = function(ev, el, fn) handlers[ev] = handlers[ev] or {} table.insert(handlers[ev], { el = el, fn = fn }) return true end
E.addCommandHandler = function(n, fn) cmds[n] = fn end
function E_fire(ev, src, ...) for _, h in ipairs({ table.unpack(handlers[ev] or {}) }) do E.source = src h.fn(...) end E.source = nil end
E.triggerEvent = function(ev, src, ...) E_fire(ev, src, ...) return true end
E.triggerClientEvent = function(target, ev, src, ...) dbg[#dbg + 1] = "toClient:" .. ev end
E.outputDebugString = function(m) dbg[#dbg + 1] = m end
E.outputChatBox = function(m) chat[#chat + 1] = m end
E.getTickCount = function() return now end
E.setTimer = function(fn, ms, n) local t = { fn = fn, ms = ms, n = n, nxt = now + ms, alive = true } timers[#timers + 1] = t return t end
E.killTimer = function(t) t.alive = false return true end
E.isElement = function(e) return type(e) == "table" and e.alive == true end
E.destroyElement = function(e) e.alive = false return true end
E.getElementPosition = function(e) return e.x, e.y, e.z end
E.setElementPosition = function(e, x, y, z) e.x, e.y, e.z = x, y, z return true end
E.getElementVelocity = function(e) return 0, 0, 0 end
E.setElementVelocity = function() return true end
E.getElementDimension = function(e) return e.dim or 0 end
E.getElementsByType = function(t) if t == "player" then return players end local l = {} for _, e in ipairs(elems) do if e.kind == t and e.alive then l[#l + 1] = e end end return l end
E.getElementData = function(e, k) return e.data and e.data[k] end
E.setElementData = function(e, k, v) e.data = e.data or {} e.data[k] = v return true end
E.getElementHealth = function(e) return e.hp end
E.setElementHealth = function(e, h) e.hp = math.max(0, math.min(h, e.maxhp or 100)) if e.kind == "ped" and e.hp <= 0 then E.killPed(e) end return true end
E.isPedDead = function(e) return e.dead == true end
E.getPedArmor = function(e) return e.armor or 0 end
E.setPedArmor = function(e, a) e.armor = a return true end
E.getPedOccupiedVehicle = function(e) return e.veh end
E.getPedMoveState = function(e) return e.move or "stand" end
E.isPedDucked = function(e) return false end
E.getPedRotation = function(e) return e.rz or 0 end
E.setPedRotation = function(e, r) e.rz = r % 360 return true end
E.setPedControlState = function(e, n, on) e.cs = e.cs or {} e.cs[n] = on return true end
E.setPedWalkingStyle = function(e, s) e.style = s return true end
E.setPedFightingStyle = function(e, s) e.fstyle = s return true end
E.setPedStat = function(e, s, v) e.maxhp = 176 return true end
E.setPedAnimation = function(e, b, a, t) e.anim = b and (b .. "/" .. a) or nil e.animUntil = now + (t or 0) e.anims = (e.anims or 0) + 1 return true end
E.createPed = function(skin, x, y, z, rz) return new("ped", { skin = skin, x = x, y = y, z = z, rz = rz or 0, hp = 100, maxhp = 100, dead = false, cs = {}, dim = 0 }) end
E.killPed = function(e, killer, weapon, bp)
    if e.dead then return true end
    e.dead, e.hp = true, 0
    if e.kind == "ped" then E_fire("onPedWasted", e, 0, killer, weapon, bp) end
    return true
end
E.setElementHealthVeh = nil
E.getPlayerAccount = function() return "acc" end
E.isGuestAccount = function() return false end
E.getAccountName = function() return "tester" end
E.isObjectInACLGroup = function() return true end
E.aclGetGroup = function() return "g" end

local function loadfile_env(path)
    local f = assert(io.open(path, "rb")) local src = f:read("a") f:close()
    local fn, err = load(src, "@" .. path, "t", E)
    assert(fn, err)
    return fn()
end
loadfile_env(RES .. "/zombie_nodes.lua")
loadfile_env(RES .. "/boundary.lua")
loadfile_env(RES .. "/zombies.lua")

local function runTimers(stop)
    while true do
        local best
        for _, t in ipairs(timers) do if t.alive and t.nxt <= stop and (not best or t.nxt < best.nxt) then best = t end end
        if not best then break end
        now = best.nxt
        if best.n == 1 then best.alive = false else best.nxt = best.nxt + best.ms end
        best.fn()
    end
    now = stop
end

local FP = E.AF_FOOTPRINTS
local function inFootprint(lx, ly, m)
    for _, r in ipairs(FP) do if lx > r[1] - m and lx < r[3] + m and ly > r[2] - m and ly < r[4] + m then return true end end
    return false
end
local moved = {}
local function physics(dt)
    for _, e in ipairs(elems) do
        if e.kind == "ped" and e.alive and not e.dead then
            local busy = e.animUntil and now < e.animUntil
            if e.cs.forwards and not busy then
                local sp = e.cs.sprint and 6.5 or (e.cs.walk and 1.6 or 4.0)
                local r = math.rad(e.rz)
                local nx, ny = e.x - math.sin(r) * sp * dt, e.y + math.cos(r) * sp * dt
                if not inFootprint(nx, ny, 0.0) then
                    moved[e] = (moved[e] or 0) + math.sqrt((nx - e.x) ^ 2 + (ny - e.y) ^ 2)
                    e.x, e.y = nx, ny
                end
            end
        end
    end
end
local function sim(seconds)
    local step = 50
    for _ = 1, math.floor(seconds * 1000 / step) do
        runTimers(now + step)
        physics(step / 1000)
    end
end
local function peds(alive_only)
    local l = {}
    for _, e in ipairs(elems) do if e.kind == "ped" and e.alive and (not alive_only or not e.dead) then l[#l + 1] = e end end
    return l
end
local function dist(a, b) return math.sqrt((a.x - b.x) ^ 2 + (a.y - b.y) ^ 2) end
local function errors() local n = 0 for _, m in ipairs(dbg) do if tostring(m):find("AI error", 1, true) then n = n + 1 end end return n end
local function states()
    local s = {}
    for _, e in ipairs(peds(true)) do local k = e.data and e.data["af:zs"] or "?" s[k] = (s[k] or 0) + 1 end
    return s
end
local CITY = { zoff = 0, ax = 0, ay = 0, az = 900 }

print("-- load")
check(#E.AF_NODES > 3000, #E.AF_NODES .. " nodes")
local links = 0
for _, n in ipairs(E.AF_NODES) do links = links + #n[5] end
check(links > 15000, links .. " links")
local pa = E.AF_FindPath(1, #E.AF_NODES)
check(pa and #pa > 20, "A* finds a path between the first and the last node (" .. (pa and #pa or 0) .. " nodes)")
local t0 = os.clock() for _ = 1, 20 do E.AF_FindPath(1 + _ * 50, #E.AF_NODES - _ * 50) end
check((os.clock() - t0) / 20 < 0.05, string.format("A* across the whole city takes %.1f ms", (os.clock() - t0) / 20 * 1000))

print("\n-- spawn")
P.x, P.y, P.z = 0, -62, 901
E.AF_ZOMBIES_CITY(CITY, true)
E.AF_BOUNDARY_CITY(CITY)
check(#peds() == 0, "no zombies before a client reports the city")
E_fire("city:ready", E.resourceRoot) -- no client yet -> must be ignored
check(#peds() == 0, "ready without a client is ignored")
E.client = P
E_fire("city:ready", E.resourceRoot)
E.client = nil
local c = peds()
check(#c == E.AF_ZCFG.MAX, #c .. " zombies spawned (MAX " .. E.AF_ZCFG.MAX .. ")")
local skins, bad = {}, 0
for _, e in ipairs(c) do skins[e.skin] = (skins[e.skin] or 0) + 1 if dist(e, P) < 40 then bad = bad + 1 end end
check(skins[48] and skins[78] and skins[79] and skins[80] and not next({}) , "skins used: 48=" .. tostring(skins[48]) .. " 78=" .. tostring(skins[78]) .. " 79=" .. tostring(skins[79]) .. " 80=" .. tostring(skins[80]))
local only = true for k in pairs(skins) do if k ~= 48 and k ~= 78 and k ~= 79 and k ~= 80 then only = false end end
check(only, "only the four existing GTA skins are used")
check(bad == 0, "nobody spawns within 40 m of the player")
local inside = 0 for _, e in ipairs(c) do if inFootprint(e.x, e.y, 0) then inside = inside + 1 end end
check(inside == 0, "nobody spawns inside a building")

print("\n-- patrol (player far away and quiet)")
local x0 = {} for _, e in ipairs(c) do x0[e] = { e.x, e.y } end
P.x, P.y, P.z = 0, -168, 901
sim(90)
local mv, still = 0, 0
for _, e in ipairs(c) do local d = math.sqrt((e.x - x0[e][1]) ^ 2 + (e.y - x0[e][2]) ^ 2) mv = mv + d if d < 3 then still = still + 1 end end
check(mv / #c > 15, string.format("zombies wander (mean displacement %.0f m in 90 s)", mv / #c))
check(still <= 6, still .. " zombies barely moved")
local ins = 0 for _, e in ipairs(c) do if inFootprint(e.x - 0, e.y - 0, 0) then ins = ins + 1 end end
check(ins == 0, "no patrolling zombie ends inside a building")
check(errors() == 0, "no AI errors (" .. errors() .. ")")
local st = states() local s = "" for k, v in pairs(st) do s = s .. k .. "=" .. v .. " " end
print("  states: " .. s)

print("\n-- sight, chase, attack")
local victim, px, py
local function clear(x1, y1, x2, y2)
    for t = 0, 1, 0.02 do if inFootprint(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, 1.0) then return false end end
    return true
end
for _, e in ipairs(c) do
    if e.skin == 48 and not victim and math.abs(e.x) < 150 and math.abs(e.y) < 150 and e.cs.forwards then
        local r = math.rad(e.rz)
        local qx, qy = e.x - math.sin(r) * 12, e.y + math.cos(r) * 12
        if math.abs(qx) < 165 and math.abs(qy) < 165 and not inFootprint(qx, qy, 1.5) and clear(e.x, e.y, qx, qy) then victim, px, py = e, qx, qy end
    end
end
assert(victim, "no suitable test zombie")
P.x, P.y, P.z, P.hp, P.armor, P.move, P.dead = px, py, 901, 100, 0, "sprint", false
victim.rz = victim.rz
sim(2)
check(victim.data["af:zs"] == "chase" or victim.data["af:zs"] == "attack", "a zombie that sees a sprinting player starts chasing (" .. tostring(victim.data["af:zs"]) .. ")")
P.move = "stand"
local hp0 = P.hp
sim(12)
check(P.hp < hp0 or P.dead, string.format("the zombie reaches the player and hurts him (hp %.0f -> %.0f)", hp0, P.hp))
check((victim.anims or 0) > 0, "melee animation played (" .. tostring(victim.anims) .. " attacks)")
local dtoP = dist(victim, P)
check(dtoP < 3.5 or P.dead, string.format("the zombie stays on him (%.1f m)", dtoP))

print("\n-- armour absorbs")
P.hp, P.armor, P.dead = 100, 100, false
local before = P.armor
sim(8)
check(P.armor < before, string.format("armour is consumed first (%.0f -> %.0f)", before, P.armor))

print("\n-- losing a target")
-- player gets teleported far away: the chasers lose him and go back to patrol
P.x, P.y, P.hp, P.armor, P.dead = 0, 160, 100, 0, false
sim(40)
local still_chasing = 0 for _, e in ipairs(peds(true)) do local s2 = e.data["af:zs"] if (s2 == "chase" or s2 == "attack") and dist(e, P) > 60 then still_chasing = still_chasing + 1 end end
check(still_chasing == 0, "nobody keeps chasing a player who is far away")
check(errors() == 0, "no AI errors")

print("\n-- path finding around a building")
local zz = nil
for _, e in ipairs(peds(true)) do if e.skin == 48 then zz = e break end end
for _, e in ipairs(peds(true)) do if e ~= zz then e.x, e.y = e.x, e.y end end
zz.x, zz.y, zz.z = 35.6, -95, 900
zz.rz = 0
P.x, P.y, P.z, P.hp, P.dead, P.move, P.armor = 35.6, -78, 901, 1e6, false, "sprint", 0
local mind = 1e9
for _ = 1, 30 do sim(1) mind = math.min(mind, dist(zz, P)) end
check(mind < 2.5, string.format("the zombie walks around the building to the player (closest %.1f m)", mind))
P.move = "stand"

print("\n-- hunting (players are felt through walls within 80 m)")
for _, e in ipairs(peds(true)) do e.x, e.y, e.z = 150, 150, 900 end
local hz = peds(true)[3]
hz.x, hz.y = 35.6, -95
P.x, P.y, P.z, P.hp, P.dead, P.move = 35.6, -150, 901, 1e6, false, "stand"       -- 55 m away, a whole block between them
sim(1)
local hmin = 1e9
for _ = 1, 40 do sim(1) hmin = math.min(hmin, dist(hz, P)) end
check(hmin < 3, string.format("a zombie 55 m away hunts a standing player through the streets (closest %.1f m)", hmin))
P.dead, P.hp = false, 100
E.AF_ZCFG.HUNT_RADIUS = 0
for _, e in ipairs(peds(true)) do e.x, e.y, e.z = 150, 150, 900 end
hz.x, hz.y = 35.6, -95
sim(15)
check(hz.data["af:zs"] ~= "chase" and hz.data["af:zs"] ~= "attack", "with HUNT_RADIUS = 0 the same zombie ignores a quiet player (" .. tostring(hz.data["af:zs"]) .. ")")
E.AF_ZCFG.HUNT_RADIUS = 80

print("\n-- invisible border")
P.dead, P.hp, P.move = false, 100, "stand"
P.x, P.y, P.z = 480, 0, 901
sim(1)
P.x, P.y = 500, 0                                   -- stepped over the 497 m line
sim(1)
check(P.x < 497 and P.x > 470, string.format("a player who crosses the border is put back (x %.1f)", P.x))
check(chat[#chat]:find("mountains") ~= nil, "...and told why")
P.x, P.y, P.z = 0, 480, 901
sim(1)
P.x, P.y, P.z = 0, 480, 1140                       -- jetpack over the mountains
sim(1)
check(P.z < 1000, string.format("a player who is too high is put back (z %.0f)", P.z))
P.x, P.y, P.z = 900, 900, 901                       -- teleported in from far outside: not touched
sim(1)
P.x, P.y = 905, 900
sim(1)
check(P.x == 905, "a player who comes from outside is left alone")
P.x, P.y, P.z = 0, 0, 901
sim(1)
P.x, P.y, P.z = 300, 0, 901
sim(1)
check(P.x == 300, "walking inside the border is free")

print("\n-- gun shot noise")
local near = nil for _, e in ipairs(peds(true)) do if dist(e, { x = 0, y = 160 }) > 30 and dist(e, { x = 0, y = 160 }) < 60 then near = e break end end
P.x, P.y, P.dead, P.hp, P.move = 0, 160, false, 100, "stand"
local listener = peds(true)[2]
listener.x, listener.y, listener.z = 40, 160, 900
E_fire("onPlayerWeaponFire", P, 30)
sim(1)
local alerted = 0 for _, e in ipairs(peds(true)) do local s2 = e.data["af:zs"] if (s2 == "chase" or s2 == "search") and dist(e, P) < 95 then alerted = alerted + 1 end end
check(alerted >= 1 and (listener.data["af:zs"] == "chase" or listener.data["af:zs"] == "search"), alerted .. " zombies react to a rifle shot (the one 40 m away: " .. tostring(listener.data["af:zs"]) .. ")")

print("\n-- being shot")
local z = peds(true)[1]
z.hp = 100
E.client = P
P.x, P.y = z.x + 5, z.y
local w0 = z.hp
E_fire("zombie:hit", E.resourceRoot, z, 31, 9, 40)
check(z.dead, "a head shot kills a walker / shambler / runner")
local brute for _, e in ipairs(peds(true)) do if e.skin == 80 then brute = e break end end
P.x, P.y = brute.x + 5, brute.y
brute.hp = 176
E_fire("zombie:hit", E.resourceRoot, brute, 31, 9, 40)
check(not brute.dead and brute.hp < 176, "a brute survives a head shot but loses " .. (176 - brute.hp) .. " hp")
check(brute.data["af:zs"] == "chase", "the shot zombie turns on the shooter")
E.client = nil
E_fire("zombie:hit", E.resourceRoot, brute, 31, 9, 40)
check(true, "hits without a client are ignored")
local n_alive = #peds(true)

print("\n-- corpse, respawn")
sim(21)
check(not z.alive, "the corpse is removed after 20 s")
sim(12)
check(#peds(true) == E.AF_ZCFG.MAX, "the population is refilled (" .. #peds(true) .. " alive)")

print("\n-- commands")
cmds.zombies(P, "zombies", "off")
check(#peds() == 0, "/zombies off removes them")
sim(25)
check(#peds() == 0, "...and nothing respawns")
cmds.zombies(P, "zombies", "on")
check(#peds(true) == E.AF_ZCFG.MAX, "/zombies on refills (" .. #peds(true) .. ")")
cmds.zombies(P, "zombies", "count", "10")
cmds.zombies(P, "zombies", "clear")
check(#peds() == 0, "/zombies clear")
cmds.zombies(P, "zombies", "on")
check(#peds(true) >= 8, "/zombies count 10 -> " .. #peds(true))
cmds.zombies(P, "zombies", "count", "34")
local before_n = #peds()
cmds.zombies(P, "zombies", "spawn", "80")
check(#peds() == before_n + 1 and peds()[#peds()].skin == 80, "/zombies spawn 80 spawns a brute")
cmds.zombies(P, "zombies", "status")
check(chat[#chat]:find("walker") ~= nil, "status text")

print("\n-- city hide / cityz")
local y0 = peds(true)[1].z
CITY.zoff = 2
E.AF_ZOMBIES_CITY(CITY)
check(math.abs(peds(true)[1].z - y0 - 2) < 0.01, "/cityz moves the zombies with the city")
E.AF_ZOMBIES_CITY(nil)
check(#peds() == 0, "hidecity removes all zombies")
sim(40)
check(#peds() == 0, "nothing respawns while the city is hidden")
check(errors() == 0, "no AI errors in the whole run")
print(string.format("\n%d checks, %d failed", checks, fails))
return fails
