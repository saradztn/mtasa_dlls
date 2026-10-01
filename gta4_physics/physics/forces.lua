GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
G4.Math = G4.Math or {}
local M = G4.Math

function M.clamp(value, low, high)
    value = G4.safeNumber(value, 0)
    return math.max(low, math.min(high, value))
end
function M.lerp(a, b, t) return a + (b - a) * M.clamp(t, 0, 1) end
function M.sign(value) return value < 0 and -1 or (value > 0 and 1 or 0) end
function M.approach(current, target, rate, dt)
    local alpha = 1 - math.exp(-math.max(0, rate) * math.max(0, dt))
    return current + (target - current) * alpha
end
function M.dot(a, b) return a.x * b.x + a.y * b.y + a.z * b.z end
function M.add(a, b) return { x = a.x + b.x, y = a.y + b.y, z = a.z + b.z } end
function M.sub(a, b) return { x = a.x - b.x, y = a.y - b.y, z = a.z - b.z } end
function M.scale(a, scalar) return { x = a.x * scalar, y = a.y * scalar, z = a.z * scalar } end
function M.length(a) return math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z) end
function M.normalize(a, fallback)
    local length = M.length(a)
    if length < 0.00001 then return fallback or { x = 0, y = 1, z = 0 } end
    return { x = a.x / length, y = a.y / length, z = a.z / length }
end
function M.cross(a, b)
    return { x = a.y * b.z - a.z * b.y, y = a.z * b.x - a.x * b.z, z = a.x * b.y - a.y * b.x }
end
function M.atan2(y, x)
    if math.atan2 then return math.atan2(y, x) end
    if x > 0 then return math.atan(y / x) end
    if x < 0 and y >= 0 then return math.atan(y / x) + math.pi end
    if x < 0 and y < 0 then return math.atan(y / x) - math.pi end
    if y > 0 then return math.pi * 0.5 end
    if y < 0 then return -math.pi * 0.5 end
    return 0
end
function M.toWorld(basis, localRight, localForward, localUp)
    return {
        x = basis.right.x * localRight + basis.forward.x * localForward + basis.up.x * localUp,
        y = basis.right.y * localRight + basis.forward.y * localForward + basis.up.y * localUp,
        z = basis.right.z * localRight + basis.forward.z * localForward + basis.up.z * localUp
    }
end
function M.toLocal(basis, world)
    return { right = M.dot(basis.right, world), forward = M.dot(basis.forward, world), up = M.dot(basis.up, world) }
end
function M.limitVector(v, maximum)
    local length = M.length(v)
    if length <= maximum or length < 0.000001 then return v end
    return M.scale(v, maximum / length)
end
function M.expSmoothing(rate, dt) return 1 - math.exp(-math.max(0, rate) * math.max(0, dt)) end
