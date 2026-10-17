--[[
  NextGenPoliceDepartment - shared math helpers.
  All coordinates in NGPD_DATA are building-local; these helpers apply the active world transform.
]]

NGPD = NGPD or {}
NGPD.origin = { x = NGPD_CONFIG.origin.x, y = NGPD_CONFIG.origin.y, z = NGPD_CONFIG.origin.z, rz = NGPD_CONFIG.origin.rz }

function NGPD.setOrigin(x, y, z, rz)
    NGPD.origin = { x = tonumber(x) or 0, y = tonumber(y) or 0, z = tonumber(z) or 0, rz = (tonumber(rz) or 0) % 360 }
end

-- local (lx, ly, lz) -> world
function NGPD.toWorld(lx, ly, lz)
    local o = NGPD.origin
    local a = math.rad(o.rz)
    local c, s = math.cos(a), math.sin(a)
    return o.x + lx * c - ly * s, o.y + lx * s + ly * c, o.z + (lz or 0)
end

-- world -> local
function NGPD.toLocal(wx, wy, wz)
    local o = NGPD.origin
    local a = math.rad(o.rz)
    local c, s = math.cos(a), math.sin(a)
    local dx, dy = wx - o.x, wy - o.y
    return dx * c + dy * s, -dx * s + dy * c, (wz or 0) - o.z
end

-- local rotation around Z -> world rotation
function NGPD.toWorldRot(rz)
    return ((rz or 0) + NGPD.origin.rz) % 360
end

function NGPD.dist3(ax, ay, az, bx, by, bz)
    local dx, dy, dz = ax - bx, ay - by, az - bz
    return math.sqrt(dx * dx + dy * dy + dz * dz)
end

-- door centre in world space (for proximity checks / prompts); z at mid-height
function NGPD.doorCentre(d)
    return NGPD.toWorld(d.x, d.y, d.z + math.min(d.h or 2.2, 2.2) * 0.5)
end

function NGPD.findDoor(id)
    if not NGPD.doorIndex then
        NGPD.doorIndex = {}
        for i, d in ipairs(NGPD_DATA.doors) do NGPD.doorIndex[d.id] = i end
    end
    local i = NGPD.doorIndex[id]
    return i and NGPD_DATA.doors[i] or nil
end

-- which room (local rect test) contains a local point; floor from z
function NGPD.roomAt(lx, ly, lz)
    local fh = NGPD_DATA.floorHeight or 5
    local fl = math.floor(((lz or 0) + 0.5) / fh)
    for _, r in ipairs(NGPD_DATA.rooms) do
        if r.floor == fl then
            for _, q in ipairs(r.rects) do
                if lx >= q[1] and lx <= q[3] and ly >= q[2] and ly <= q[4] then return r end
            end
        end
    end
    return nil
end

-- is the local point inside the building footprint (used for interior shader instances / weather)
function NGPD.isInsideBuilding(lx, ly, lz)
    if lz and (lz < -1 or lz > 16) then return false end
    return lx > -42 and lx < 42 and ly > -14 and ly < 18
end

function NGPD.clamp(v, a, b) if v < a then return a elseif v > b then return b end return v end
function NGPD.lerp(a, b, t) return a + (b - a) * t end
