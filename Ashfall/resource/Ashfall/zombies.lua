-- Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA resource
-- ---------------------------------------------------------------------------------------------
-- zombies.lua (server) - the infected of District Zero.
--   * 4 zombie types, each one an EXISTING GTA:SA ped skin (no custom skins - they can be swapped later in ZTYPES below):
--         48 walker | 78 shambler | 79 runner | 80 brute
--   * AI: patrol the walk-node graph (zombie_nodes.lua, A* path finding), sight (distance + view cone + line of sight against the
--     building footprints), hearing (running / sprinting, gun shots), reaction delay, chase, search the last known position,
--     give up, horde alert, stuck detection, fall guard
--   * combat: melee attack with animation + damage (armour absorbs part of it), hits on vehicles, damage by the players (hits are
--     forwarded by zombies_client.lua, head shots kill), stagger, death, corpse clean-up, respawn out of the players' sight
--   * the zombies live exactly as long as the city is shown; they are spawned after a client reports the city as built ("city:ready")
--   * server events for future development:  "zombie:spawned" (ped, typeName)  "zombie:killed" (ped, killer)  "zombie:attack" (ped, player, damage)
--   * commands: /zombies [on|off|clear|status|spawn <type|skin>|count <n>]
-- ---------------------------------------------------------------------------------------------
AF_ZCFG = {
    ENABLED = true,
    MAX = 34,                 -- zombies alive at the same time (spread over the types by their weights)
    TICK = 250,               -- AI step (ms)
    RESPAWN_MS = 30000,
    CORPSE_MS = 20000,
    SPAWN_MIN_DIST = 40,      -- a zombie never (re)spawns closer than this to a player
    ZONE = 235,               -- players further than this from the city centre are ignored
    ADMIN_ONLY = false,
}

-- skin = GTA:SA ped model id, hp (max 176), style = setPedWalkingStyle, chase = walk | run | sprint, dmg per hit, cd = seconds between hits,
-- reach (m), sight (m), fov (deg), hear = hearing multiplier, react = seconds until a sensed player is noticed, turn = deg/s, weight = share of MAX
AF_ZTYPES = {
    walker   = { skin = 48, hp = 100, style = 126, chase = "run",    dmg = 8,  cd = 1.2, reach = 1.5, sight = 30, fov = 150, hear = 1.0, react = 0.55, turn = 140, weight = 14, fight = 4 },
    shambler = { skin = 78, hp = 70,  style = 120, chase = "walk",   dmg = 6,  cd = 1.3, reach = 1.4, sight = 22, fov = 130, hear = 1.4, react = 0.80, turn = 90,  weight = 10, fight = 4 },
    runner   = { skin = 79, hp = 80,  style = 125, chase = "sprint", dmg = 7,  cd = 0.9, reach = 1.5, sight = 36, fov = 160, hear = 1.2, react = 0.30, turn = 220, weight = 6,  fight = 4 },
    brute    = { skin = 80, hp = 176, style = 56,  chase = "run",    dmg = 20, cd = 1.7, reach = 1.8, sight = 28, fov = 140, hear = 0.9, react = 0.65, turn = 100, weight = 4,  fight = 5 },
}
local TYPE_ORDER = { "walker", "shambler", "runner", "brute" }
local ATTACK_ANIMS = { { "FIGHT_B", "FightB_1" }, { "FIGHT_B", "FightB_2" }, { "FIGHT_B", "FightB_3" } }
local MOVE_FACTOR = { sprint = 1.0, jog = 0.65, powerwalk = 0.4, walk = 0.3, crouch = 0.12, crawl = 0.1, stand = 0.04, jump = 0.5, fall = 0.2, climb = 0.4 }
local SHOT_RADIUS = { [22] = 45, [23] = 12, [24] = 75, [25] = 85, [26] = 85, [27] = 85, [28] = 60, [29] = 55, [30] = 95, [31] = 95, [32] = 60, [33] = 95, [34] = 110 }
local KIND_WEIGHT = { [1] = 1, [2] = 1, [3] = 3, [4] = 2 }

addEvent("city:ready", true)
addEvent("zombie:hit", true)
addEvent("zombie:spawned", false)
addEvent("zombie:killed", false)
addEvent("zombie:attack", false)

local W = nil                 -- { x, y, z } world position of the city origin (z includes /cityz trims) or nil
local EPOCH = 0               -- bumped whenever the city is shown / hidden so stale timers do nothing
local Zs = {}                 -- list of zombie records
local ZOf = {}                -- ped -> record
local ready = {}              -- player -> true once his client built the city
local nowMs = function() return getTickCount() end
local rnd = function(a, b) return a + (b - a) * math.random() end

local function dbg(m) outputDebugString("[Ashfall zombies] " .. m, 3) end

-- ---------------------------------------------------------------------------------------------
-- node graph, A*
-- ---------------------------------------------------------------------------------------------
local NODES = AF_NODES or {}
local GRID = {}               -- cell key -> node index
local CELL = AF_NODE_CELL or 4.0
local HALFX = 170
local function ckey(i, j) return i * 1000 + j end
for n, nd in ipairs(NODES) do
    local i, j = math.floor((nd[1] + HALFX) / CELL), math.floor((nd[2] + HALFX) / CELL)
    GRID[ckey(i, j)] = n
end

local function nearestNode(lx, ly)
    local ci, cj = math.floor((lx + HALFX) / CELL), math.floor((ly + HALFX) / CELL)
    local best, bd = nil, 1e9
    for r = 0, 6 do
        for i = ci - r, ci + r do
            for j = cj - r, cj + r do
                if r == 0 or math.abs(i - ci) == r or math.abs(j - cj) == r then
                    local n = GRID[ckey(i, j)]
                    if n then
                        local nd = NODES[n]
                        local d = (nd[1] - lx) ^ 2 + (nd[2] - ly) ^ 2
                        if d < bd then best, bd = n, d end
                    end
                end
            end
        end
        if best and r >= 1 then break end
    end
    return best, math.sqrt(bd)
end

local function heapPush(h, f, n)
    local i = #h + 1
    h[i] = { f, n }
    while i > 1 do
        local p = math.floor(i / 2)
        if h[p][1] <= h[i][1] then break end
        h[p], h[i] = h[i], h[p]
        i = p
    end
end
local function heapPop(h)
    local top = h[1]
    local last = table.remove(h)
    if #h > 0 then
        h[1] = last
        local i = 1
        while true do
            local l, r, s = i * 2, i * 2 + 1, i
            if l <= #h and h[l][1] < h[s][1] then s = l end
            if r <= #h and h[r][1] < h[s][1] then s = r end
            if s == i then break end
            h[s], h[i] = h[i], h[s]
            i = s
        end
    end
    return top
end

-- returns a list of node indices from a to b (or nil)
function AF_FindPath(a, b)
    if not a or not b then return nil end
    if a == b then return { a } end
    local gx, gy = NODES[b][1], NODES[b][2]
    local open, g, came, closed = {}, { [a] = 0 }, {}, {}
    heapPush(open, 0, a)
    local steps = 0
    while #open > 0 and steps < 6000 do
        local cur = heapPop(open)[2]
        if cur == b then
            local path, c = {}, b
            while c do table.insert(path, 1, c) c = came[c] end
            return path
        end
        if not closed[cur] then
            closed[cur] = true
            steps = steps + 1
            local cn = NODES[cur]
            for _, nb in ipairs(cn[5]) do
                if not closed[nb] then
                    local nn = NODES[nb]
                    local ng = g[cur] + math.sqrt((nn[1] - cn[1]) ^ 2 + (nn[2] - cn[2]) ^ 2)
                    if not g[nb] or ng < g[nb] then
                        g[nb], came[nb] = ng, cur
                        heapPush(open, ng + math.sqrt((nn[1] - gx) ^ 2 + (nn[2] - gy) ^ 2), nb)
                    end
                end
            end
        end
    end
    return nil
end

-- ---------------------------------------------------------------------------------------------
-- geometry helpers
-- ---------------------------------------------------------------------------------------------
local function findRotation(x1, y1, x2, y2)
    local t = -math.deg(math.atan2(x2 - x1, y2 - y1))
    return t < 0 and t + 360 or t
end
local function angDiff(a, b)       -- signed shortest difference b - a in degrees
    local d = (b - a) % 360
    if d > 180 then d = d - 360 end
    return d
end

-- 2D segment against the building footprints (local city frame)
local function segHitsRect(ax, ay, bx, by, r, m)
    local dx, dy = bx - ax, by - ay
    local t0, t1 = 0, 1
    local function clip(p, q)
        if p == 0 then return q >= 0 end
        local t = q / p
        if p < 0 then if t > t1 then return false end if t > t0 then t0 = t end
        else if t < t0 then return false end if t < t1 then t1 = t end end
        return true
    end
    return clip(-dx, ax - (r[1] - m)) and clip(dx, (r[3] + m) - ax) and clip(-dy, ay - (r[2] - m)) and clip(dy, (r[4] + m) - ay)
end
local function losClear(lax, lay, lbx, lby, m)
    m = m or 0
    for _, r in ipairs(AF_FOOTPRINTS or {}) do
        if segHitsRect(lax, lay, lbx, lby, r, m) then return false end
    end
    return true
end

-- ---------------------------------------------------------------------------------------------
-- players
-- ---------------------------------------------------------------------------------------------
local noise = {}              -- player -> { x, y, r, t }   (gun shots)

local function livePlayers()
    local list = {}
    if not W then return list end
    for _, p in ipairs(getElementsByType("player")) do
        if isElement(p) and not isPedDead(p) and getElementDimension(p) == 0 then
            local x, y, z = getElementPosition(p)
            if math.abs(x - W.x) < AF_ZCFG.ZONE and math.abs(y - W.y) < AF_ZCFG.ZONE and z > W.z - 20 and z < W.z + 90 then
                list[#list + 1] = { p = p, x = x, y = y, z = z }
            end
        end
    end
    return list
end

local function hurtPlayer(p, dmg, zped)
    if isPedDead(p) then return end
    local veh = getPedOccupiedVehicle(p)
    if veh then
        setElementHealth(veh, math.max(250, getElementHealth(veh) - dmg * 4))      -- zombies batter the car, they cannot pull you out
        return
    end
    local arm = getPedArmor(p)
    if arm > 0 then
        local a = math.min(arm, dmg * 0.6)
        setPedArmor(p, arm - a)
        dmg = dmg - a
    end
    local hp = getElementHealth(p) - dmg
    if hp <= 0 then
        killPed(p, zped, 0, 3)
    else
        setElementHealth(p, hp)
    end
    triggerClientEvent(p, "zombie:hurt", resourceRoot, dmg, getElementPosition(zped))
end

-- ---------------------------------------------------------------------------------------------
-- zombie records
-- ---------------------------------------------------------------------------------------------
local function setState(z, st)
    if z.state == st then return end
    z.state = st
    z.path, z.pi = nil, nil
    z.searchGiven, z.searchUntil = nil, nil
    if isElement(z.ped) then setElementData(z.ped, "af:zs", st, true) end
end

local function control(z, name, on)
    z.cs = z.cs or {}
    if z.cs[name] ~= on then
        z.cs[name] = on
        setPedControlState(z.ped, name, on)
    end
end
local function halt(z)
    control(z, "forwards", false) control(z, "walk", false) control(z, "sprint", false)
end

local function pickSpawnNode(players, minDist)
    for _ = 1, 40 do
        local n = math.random(#NODES)
        local nd = NODES[n]
        if math.random() * 3 < (KIND_WEIGHT[nd[4]] or 1) then
            local ok = true
            local wx, wy = W.x + nd[1], W.y + nd[2]
            for _, pl in ipairs(players) do
                if (pl.x - wx) ^ 2 + (pl.y - wy) ^ 2 < minDist * minDist then ok = false break end
            end
            if ok then return n end
        end
    end
    return nil
end

local function countOf(typeKey)
    local n = 0
    for _, z in ipairs(Zs) do if z.type == typeKey and not z.dead then n = n + 1 end end
    return n
end

local function quota(typeKey)
    local tw = 0
    for _, k in ipairs(TYPE_ORDER) do tw = tw + AF_ZTYPES[k].weight end
    return math.max(1, math.floor(AF_ZCFG.MAX * AF_ZTYPES[typeKey].weight / tw + 0.5))
end

local function spawnZombie(typeKey, node, wx, wy, wz)
    local T = AF_ZTYPES[typeKey]
    if not T or not W then return nil end
    local x, y, zz
    if node then
        local nd = NODES[node]
        x, y, zz = W.x + nd[1], W.y + nd[2], W.z + nd[3] + 1.0
    else
        x, y, zz = wx, wy, wz
    end
    local ped = createPed(T.skin, x, y, zz, math.random(0, 359))
    if not ped then return nil end
    pcall(setPedWalkingStyle, ped, T.style)
    pcall(setPedFightingStyle, ped, T.fight or 4)
    if T.hp > 100 then pcall(setPedStat, ped, 24, 1000) end
    setElementHealth(ped, T.hp)
    setElementData(ped, "af:zombie", typeKey, true)
    setElementData(ped, "af:zs", "idle", true)
    local z = { ped = ped, type = typeKey, T = T, state = "idle", born = nowMs(), epoch = EPOCH, sense = 0, nextAttack = 0, home = node,
                lastPos = { x, y }, stuck = 0, idleUntil = nowMs() + rnd(500, 4000), spawnT = nowMs() }
    Zs[#Zs + 1] = z
    ZOf[ped] = z
    triggerEvent("zombie:spawned", resourceRoot, ped, typeKey)
    return z
end

local function removeZombie(z)
    ZOf[z.ped] = nil
    for i, o in ipairs(Zs) do if o == z then table.remove(Zs, i) break end end
    if isElement(z.ped) then destroyElement(z.ped) end
end

local function clearAll()
    for i = #Zs, 1, -1 do
        local z = Zs[i]
        ZOf[z.ped] = nil
        if isElement(z.ped) then destroyElement(z.ped) end
        Zs[i] = nil
    end
end

local function fillPopulation()
    if not W or not AF_ZCFG.ENABLED or #NODES == 0 then return end
    local players = livePlayers()
    for _, k in ipairs(TYPE_ORDER) do
        local need = quota(k) - countOf(k)
        for _ = 1, need do
            local n = pickSpawnNode(players, AF_ZCFG.SPAWN_MIN_DIST)
            if n then spawnZombie(k, n) end
        end
    end
end

-- ---------------------------------------------------------------------------------------------
-- movement
-- ---------------------------------------------------------------------------------------------
-- walk / run towards a world point; returns the remaining distance
local function steer(z, x, y, tx, ty, mode, dt)
    local want = findRotation(x, y, tx, ty)
    if z.avoid and nowMs() < z.avoid.t then want = (want + z.avoid.d) % 360 end
    local cur = getPedRotation(z.ped)
    local d = angDiff(cur, want)
    local step = z.T.turn * dt
    if math.abs(d) <= step then cur = want else cur = (cur + (d > 0 and step or -step)) % 360 end
    setPedRotation(z.ped, cur)
    local off = math.abs(angDiff(cur, want))
    control(z, "forwards", off < 75)
    control(z, "walk", mode == "walk")
    control(z, "sprint", mode == "sprint")
    return math.sqrt((tx - x) ^ 2 + (ty - y) ^ 2)
end

local function faceTo(z, x, y, tx, ty, dt)
    local want = findRotation(x, y, tx, ty)
    local cur = getPedRotation(z.ped)
    local d = angDiff(cur, want)
    local step = z.T.turn * 1.6 * dt
    if math.abs(d) <= step then cur = want else cur = (cur + (d > 0 and step or -step)) % 360 end
    setPedRotation(z.ped, cur)
end

-- follow z.path (node indices); returns true when the path is finished
local function followPath(z, x, y, mode, dt)
    local path = z.path
    if not path or not z.pi then return true end
    local nd = NODES[path[z.pi]]
    local tx, ty = W.x + nd[1], W.y + nd[2]
    local dist = steer(z, x, y, tx, ty, mode, dt)
    local reach = (z.pi == #path) and 1.2 or 1.8
    if dist < reach then
        z.pi = z.pi + 1
        if z.pi > #path then z.path, z.pi = nil, nil return true end
    end
    return false
end

local function planTo(z, x, y, gx, gy)     -- gx, gy: world goal; sets z.path
    local a = nearestNode(x - W.x, y - W.y)
    local b = nearestNode(gx - W.x, gy - W.y)
    local path = AF_FindPath(a, b)
    z.planT = nowMs()
    z.planGoal = { gx, gy }
    if path then
        z.path, z.pi = path, 1
        -- skip the first nodes that are behind us
        while z.pi < #path do
            local n1, n2 = NODES[path[z.pi]], NODES[path[z.pi + 1]]
            local d1 = (W.x + n1[1] - x) ^ 2 + (W.y + n1[2] - y) ^ 2
            local d2 = (W.x + n2[1] - x) ^ 2 + (W.y + n2[2] - y) ^ 2
            if d1 < 9 and d2 < d1 + 30 then z.pi = z.pi + 1 else break end
        end
        return true
    end
    z.path, z.pi = nil, nil
    return false
end

-- ---------------------------------------------------------------------------------------------
-- senses
-- ---------------------------------------------------------------------------------------------
-- how loud is a player: by his move state (or by his speed when the state is not available)
local function moveFactor(p)
    local ok, st = pcall(getPedMoveState, p)
    if ok and st and MOVE_FACTOR[st] then return MOVE_FACTOR[st] end
    local vx, vy = getElementVelocity(p)
    local sp = math.sqrt(vx * vx + vy * vy) * 50
    local f = sp > 5.5 and 1.0 or sp > 3.5 and 0.65 or sp > 1.5 and 0.3 or 0.04
    if isPedDucked(p) then f = f * 0.4 end
    return f
end

local function sensePlayer(z, x, y, pl, facing)
    local dx, dy = pl.x - x, pl.y - y
    local dist = math.sqrt(dx * dx + dy * dy)
    local T = z.T
    -- hearing: how loud is he?
    local f = moveFactor(pl.p)
    local heard = dist < 24 * f * T.hear
    local n = noise[pl.p]
    if n and nowMs() - n.t < 2500 and (n.x - x) ^ 2 + (n.y - y) ^ 2 < n.r * n.r then heard = true end
    -- sight: cone + line of sight
    local seen = false
    if dist < T.sight then
        local inCone = math.abs(angDiff(facing, findRotation(x, y, pl.x, pl.y))) < T.fov / 2 or dist < 5
        if inCone and losClear(x - W.x, y - W.y, pl.x - W.x, pl.y - W.y) then seen = true end
    end
    return seen, heard, dist
end

local function alertNear(z, x, y, r, pl)
    for _, o in ipairs(Zs) do
        if o ~= z and not o.dead and (o.state == "idle" or o.state == "wander") and isElement(o.ped) then
            local ox, oy = getElementPosition(o.ped)
            if (ox - x) ^ 2 + (oy - y) ^ 2 < r * r and math.random() < 0.6 then
                o.last = { pl.x, pl.y, nowMs() }
                setState(o, "search")
            end
        end
    end
end

-- ---------------------------------------------------------------------------------------------
-- one AI step for a zombie
-- ---------------------------------------------------------------------------------------------
local function doAttack(z, target, x, y)
    local T = z.T
    local a = ATTACK_ANIMS[math.random(#ATTACK_ANIMS)]
    pcall(setPedAnimation, z.ped, a[1], a[2], 700, false, false, false, false)
    z.nextAttack = nowMs() + T.cd * 1000
    local epoch, ped, tp = z.epoch, z.ped, target.p
    setTimer(function()
        if epoch ~= EPOCH or not isElement(ped) or not isElement(tp) or isPedDead(ped) or isPedDead(tp) then return end
        local zx, zy, zz = getElementPosition(ped)
        local px, py, pz = getElementPosition(tp)
        if (zx - px) ^ 2 + (zy - py) ^ 2 < (T.reach * 1.35) ^ 2 and math.abs(zz - pz) < 2.4 then
            hurtPlayer(tp, T.dmg * rnd(0.8, 1.2), ped)
            triggerEvent("zombie:attack", resourceRoot, ped, tp, T.dmg)
        end
    end, 380, 1)
end

local function think(z, players, dt)
    local ped = z.ped
    local T = z.T
    local now = nowMs()
    local x, y, zz = getElementPosition(ped)

    -- fall guard / far away guard: put the zombie back on its node
    if zz < W.z - 40 or math.abs(x - W.x) > 330 or math.abs(y - W.y) > 330 then
        local n = z.home or math.random(#NODES)
        local nd = NODES[n]
        setElementPosition(ped, W.x + nd[1], W.y + nd[2], W.z + nd[3] + 1.0)
        setElementVelocity(ped, 0, 0, 0)
        setState(z, "idle")
        return
    end

    -- stagger after a hit
    if z.stun and now < z.stun then halt(z) return end

    -- ---- senses
    local facing = getPedRotation(ped)
    local best, bestD, sawIt = nil, 1e9, false
    for _, pl in ipairs(players) do
        local seen, heard, dist = sensePlayer(z, x, y, pl, facing)
        if (seen or heard) and dist < bestD then best, bestD, sawIt = pl, dist, seen end
    end
    if best then
        z.sense = math.min(z.sense + dt, 3)
        if z.sense >= T.react or z.state == "chase" or z.state == "attack" then
            if not z.target or z.target ~= best.p or z.state == "idle" or z.state == "wander" or z.state == "search" then
                if z.state ~= "chase" and z.state ~= "attack" then
                    alertNear(z, x, y, 18, best)
                end
                z.target = best.p
                if z.state ~= "attack" then setState(z, "chase") end
            end
            z.last = { best.x, best.y, now }
            z.seen = sawIt
        end
    else
        z.sense = math.max(0, z.sense - dt * 0.7)
    end

    -- ---- target data
    local tgt
    if z.target and isElement(z.target) and not isPedDead(z.target) then
        for _, pl in ipairs(players) do if pl.p == z.target then tgt = pl break end end
    end
    if (z.state == "chase" or z.state == "attack") and not tgt then
        z.target = nil
        setState(z, z.last and "search" or "wander")
    end

    local intent = false
    -- ---- attack / chase
    if tgt and (z.state == "chase" or z.state == "attack") then
        local dx, dy = tgt.x - x, tgt.y - y
        local dist = math.sqrt(dx * dx + dy * dy)
        if dist < T.reach and math.abs(tgt.z - zz) < 2.2 then
            if z.state ~= "attack" then setState(z, "attack") end
            halt(z)
            faceTo(z, x, y, tgt.x, tgt.y, dt)
            if now >= z.nextAttack and math.abs(angDiff(getPedRotation(ped), findRotation(x, y, tgt.x, tgt.y))) < 40 then doAttack(z, tgt, x, y) end
        else
            if z.state == "attack" and dist > T.reach * 1.25 then setState(z, "chase") end
            if z.state == "chase" then
                intent = true
                local direct = losClear(x - W.x, y - W.y, tgt.x - W.x, tgt.y - W.y, 0.8)     -- body width: do not cut building corners
                if direct then
                    z.path, z.pi = nil, nil
                    steer(z, x, y, tgt.x, tgt.y, T.chase, dt)
                else
                    local g = z.planGoal
                    local need = (not g) or (not z.path and now - (z.planT or 0) > 600)
                    if z.path and g and now - (z.planT or 0) > 1500 and (g[1] - tgt.x) ^ 2 + (g[2] - tgt.y) ^ 2 > 36 then need = true end
                    if need then planTo(z, x, y, tgt.x, tgt.y) end
                    if z.path then followPath(z, x, y, T.chase, dt) else steer(z, x, y, tgt.x, tgt.y, T.chase, dt) end
                end
                if not sawIt and not best and z.last and now - z.last[3] > 6500 then
                    z.target = nil
                    setState(z, "search")
                end
            end
        end
    elseif z.state == "search" then
        intent = true
        local l = z.last
        if not l or now - l[3] > 14000 then
            setState(z, "wander")
        else
            if not z.path then
                if not z.searchGiven then
                    z.searchGiven = true
                    planTo(z, x, y, l[1], l[2])
                end
            end
            if z.path then
                followPath(z, x, y, "walk", dt)
            else
                -- arrived at the sound / the last known position: look around, then go back to patrolling
                halt(z)
                intent = false
                z.searchUntil = z.searchUntil or (now + rnd(2500, 5000))
                if now > z.searchUntil then z.searchUntil, z.searchGiven, z.last = nil, nil, nil setState(z, "wander") end
            end
        end
    else
        -- ---- idle / wander
        if z.state == "idle" then
            halt(z)
            if now >= z.idleUntil then setState(z, "wander") end
        elseif z.state == "wander" then
            intent = true
            if not z.path then
                -- choose a destination 25..90 m away
                local ok = false
                for _ = 1, 8 do
                    local n = math.random(#NODES)
                    local nd = NODES[n]
                    local d = math.sqrt((W.x + nd[1] - x) ^ 2 + (W.y + nd[2] - y) ^ 2)
                    if d > 25 and d < 90 then ok = planTo(z, x, y, W.x + nd[1], W.y + nd[2]) if ok then break end end
                end
                if not ok then z.idleUntil = now + 1500 setState(z, "idle") end
            else
                if followPath(z, x, y, "walk", dt) then
                    z.idleUntil = now + rnd(2000, 8000)
                    setState(z, "idle")
                    halt(z)
                end
            end
        end
    end
    -- ---- stuck detection (props, cars, trees, other zombies)
    if intent then
        local moved = math.sqrt((x - z.lastPos[1]) ^ 2 + (y - z.lastPos[2]) ^ 2)
        if moved < 0.12 then z.stuck = z.stuck + dt else z.stuck = 0 end
        if z.stuck > 1.0 and z.stuck < 1.0 + dt + 0.01 then
            control(z, "jump", true)
            z.avoid = { t = now + 900, d = (math.random() < 0.5 and 1 or -1) * rnd(50, 100) }
        elseif z.cs and z.cs.jump then
            control(z, "jump", false)
        end
        if z.stuck > 3.5 then
            z.path, z.pi, z.stuck = nil, nil, 0
            z.avoid = { t = now + 1500, d = rnd(-150, 150) }
        end
    else
        z.stuck = 0
        if z.cs and z.cs.jump then control(z, "jump", false) end
    end
    z.lastPos = { x, y }
end

-- ---------------------------------------------------------------------------------------------
-- main loop
-- ---------------------------------------------------------------------------------------------
local lastTick = 0
setTimer(function()
    if not W or not AF_ZCFG.ENABLED then return end
    local now = nowMs()
    local dt = math.min((now - lastTick) / 1000, 0.6)
    if lastTick == 0 then dt = AF_ZCFG.TICK / 1000 end
    lastTick = now
    local players = livePlayers()
    for i = #Zs, 1, -1 do
        local z = Zs[i]
        if z and not z.dead then
            if not isElement(z.ped) or isPedDead(z.ped) then
                z.dead = true
            else
                local ok, err = pcall(think, z, players, dt)
                if not ok then dbg("AI error: " .. tostring(err)) end
            end
        end
    end
end, AF_ZCFG.TICK, 0)

-- ---------------------------------------------------------------------------------------------
-- death, damage, noise
-- ---------------------------------------------------------------------------------------------
addEventHandler("onPedWasted", root, function(ammo, killer, weapon, bodypart)
    local z = ZOf[source]
    if not z or z.dead then return end
    z.dead = true
    local epoch, ped, typeKey = z.epoch, source, z.type
    triggerEvent("zombie:killed", resourceRoot, ped, killer)
    setTimer(function()
        if z and ZOf[ped] then removeZombie(z) end
    end, AF_ZCFG.CORPSE_MS, 1)
    setTimer(function()
        if epoch ~= EPOCH or not W or not AF_ZCFG.ENABLED then return end
        if countOf(typeKey) >= quota(typeKey) then return end
        local n = pickSpawnNode(livePlayers(), AF_ZCFG.SPAWN_MIN_DIST)
        if n then spawnZombie(typeKey, n) end
    end, AF_ZCFG.RESPAWN_MS, 1)
end)

addEventHandler("zombie:hit", resourceRoot, function(ped, weapon, bodypart, loss)
    local p = client
    local z = ZOf[ped]
    if not p or not z or z.dead or not isElement(ped) or type(weapon) ~= "number" then return end
    local px, py, pz = getElementPosition(p)
    local x, y, zz = getElementPosition(ped)
    if (px - x) ^ 2 + (py - y) ^ 2 > 140 ^ 2 then return end
    -- the hit alerts the zombie and staggers it a little
    z.target = p
    z.last = { px, py, nowMs() }
    z.sense = 3
    if z.state ~= "attack" then setState(z, "chase") end
    if (tonumber(loss) or 0) >= 12 then z.stun = nowMs() + 450 end
    if bodypart == 9 and weapon >= 22 and weapon <= 38 then            -- head shot
        if z.type == "brute" then
            setElementHealth(ped, math.max(0, getElementHealth(ped) - (tonumber(loss) or 20) * 2))
        else
            killPed(ped, p, weapon, 9)
        end
    end
end)

addEventHandler("onPlayerWeaponFire", root, function(weapon)
    if not W then return end
    local x, y, z = getElementPosition(source)
    noise[source] = { x = x, y = y, r = SHOT_RADIUS[weapon] or 50, t = nowMs() }
end)

-- ---------------------------------------------------------------------------------------------
-- city life cycle (hooks called by server.lua / client events)
-- ---------------------------------------------------------------------------------------------
function AF_ZOMBIES_CITY(city, reshow)
    if city and reshow and W then      -- the clients rebuild the city: remove the zombies, they are respawned when a client reports "city:ready"
        EPOCH = EPOCH + 1
        clearAll()
        W = nil
    end
    if not city then
        EPOCH = EPOCH + 1
        W = nil
        clearAll()
        return
    end
    local nz = city.az + city.zoff
    if W and (math.abs(W.x - city.ax) > 0.01 or math.abs(W.y - city.ay) > 0.01 or math.abs(W.base - city.az) > 0.01) then
        EPOCH = EPOCH + 1
        clearAll()
        W = nil
    end
    if W then
        local dz = nz - W.z
        if math.abs(dz) > 0.001 then
            for _, z in ipairs(Zs) do
                if isElement(z.ped) then
                    local x, y, zz = getElementPosition(z.ped)
                    setElementPosition(z.ped, x, y, zz + dz)
                end
            end
        end
        W.z = nz
    else
        EPOCH = EPOCH + 1
        W = { x = city.ax, y = city.ay, z = nz, base = city.az, spawned = false }
    end
end

addEventHandler("city:ready", resourceRoot, function()
    if not client then return end
    ready[client] = true
    if W and not W.spawned and AF_ZCFG.ENABLED then
        W.spawned = true
        fillPopulation()
        local epoch = EPOCH
        -- keep the population topped up (deaths are refilled by their own timers; this repairs everything else)
        setTimer(function() if epoch == EPOCH and W and AF_ZCFG.ENABLED then fillPopulation() end end, 20000, 0)
    end
end)

addEventHandler("onPlayerQuit", root, function() ready[source] = nil noise[source] = nil end)

-- ---------------------------------------------------------------------------------------------
-- /zombies
-- ---------------------------------------------------------------------------------------------
local function allowedZ(player)
    if not AF_ZCFG.ADMIN_ONLY then return true end
    local acc = getPlayerAccount(player)
    if not acc or isGuestAccount(acc) then return false end
    return isObjectInACLGroup("user." .. getAccountName(acc), aclGetGroup("Admin")) and true or false
end

addCommandHandler("zombies", function(player, _, a1, a2)
    if not allowedZ(player) then outputChatBox("Ashfall: you are not allowed to use this command.", player, 255, 80, 80) return end
    local function say(m) outputChatBox("#c8b090[Ashfall zombies] #ffffff" .. m, player, 255, 255, 255, true) end
    a1 = a1 and a1:lower() or "status"
    if a1 == "off" then
        AF_ZCFG.ENABLED = false
        EPOCH = EPOCH + 1
        clearAll()
        say("zombies OFF")
    elseif a1 == "on" then
        AF_ZCFG.ENABLED = true
        if W then W.spawned = true fillPopulation() end
        say("zombies ON")
    elseif a1 == "clear" then
        EPOCH = EPOCH + 1
        clearAll()
        say("all zombies removed (use /zombies on to refill)")
    elseif a1 == "count" and tonumber(a2) then
        AF_ZCFG.MAX = math.max(4, math.min(120, math.floor(tonumber(a2))))
        say("population = " .. AF_ZCFG.MAX)
        if W and AF_ZCFG.ENABLED then fillPopulation() end
    elseif a1 == "spawn" then
        if not W then say("show the city first (/showcity)") return end
        local key = a2 and a2:lower()
        if not AF_ZTYPES[key or ""] then
            for k, T in pairs(AF_ZTYPES) do if tostring(T.skin) == key then key = k end end
        end
        if not AF_ZTYPES[key or ""] then say("types: walker (48), shambler (78), runner (79), brute (80)") return end
        local x, y, z = getElementPosition(player)
        local r = math.rad(getPedRotation(player))
        spawnZombie(key, nil, x - math.sin(r) * 6, y + math.cos(r) * 6, z + 1.0)
        say("spawned a " .. key)
    else
        local c = {}
        for _, k in ipairs(TYPE_ORDER) do c[#c + 1] = k .. " (" .. AF_ZTYPES[k].skin .. ") " .. countOf(k) end
        say((AF_ZCFG.ENABLED and "ON" or "OFF") .. ", alive: " .. table.concat(c, ", ") .. "  |  /zombies on|off|clear|count <n>|spawn <type>")
    end
end)
