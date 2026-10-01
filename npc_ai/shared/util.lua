-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: SHARED UTILITIES
-- ============================================================================

NPCUtil = NPCUtil or {}

function NPCUtil.now()
    return getTickCount()
end

function NPCUtil.isFinite(value)
    return type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end

function NPCUtil.clamp(value, minimum, maximum)
    if value < minimum then
        return minimum
    end
    if value > maximum then
        return maximum
    end
    return value
end

function NPCUtil.distanceSquared(ax, ay, az, bx, by, bz)
    local dx = bx - ax
    local dy = by - ay
    local dz = (bz or 0) - (az or 0)
    return dx * dx + dy * dy + dz * dz
end

function NPCUtil.distance2D(ax, ay, bx, by)
    local dx = bx - ax
    local dy = by - ay
    return math.sqrt(dx * dx + dy * dy)
end

function NPCUtil.distance3D(ax, ay, az, bx, by, bz)
    return math.sqrt(NPCUtil.distanceSquared(ax, ay, az, bx, by, bz))
end

function NPCUtil.normalize2D(x, y)
    local length = math.sqrt(x * x + y * y)
    if length < 0.00001 then
        return 0, 0, 0
    end
    return x / length, y / length, length
end

function NPCUtil.normalizeAngle(angle)
    angle = angle % 360
    if angle < 0 then
        angle = angle + 360
    end
    return angle
end

function NPCUtil.angleDifference(fromAngle, toAngle)
    return ((toAngle - fromAngle + 540) % 360) - 180
end

function NPCUtil.approachAngle(current, target, maximumStep)
    local difference = NPCUtil.angleDifference(current, target)
    if math.abs(difference) <= maximumStep then
        return NPCUtil.normalizeAngle(target)
    end
    if difference > 0 then
        return NPCUtil.normalizeAngle(current + maximumStep)
    end
    return NPCUtil.normalizeAngle(current - maximumStep)
end

-- GTA/MTA ped Z rotation: 0 faces positive Y, 90 faces negative X.
function NPCUtil.rotationFromVector(dx, dy)
    return NPCUtil.normalizeAngle(math.deg(math.atan2(-dx, dy)))
end

function NPCUtil.vectorFromRotation(rotation)
    local radians = math.rad(rotation)
    return -math.sin(radians), math.cos(radians)
end

function NPCUtil.makeNodeId(area, nodeId)
    return area * 65536 + nodeId
end

function NPCUtil.splitNodeId(globalId)
    local area = math.floor(globalId / 65536)
    return area, globalId - area * 65536
end

function NPCUtil.copyArray(source)
    local result = {}
    for index = 1, #source do
        result[index] = source[index]
    end
    return result
end

function NPCUtil.copyTable(source)
    if type(source) ~= "table" then
        return source
    end

    local result = {}
    for key, value in pairs(source) do
        if type(value) == "table" then
            result[key] = NPCUtil.copyTable(value)
        else
            result[key] = value
        end
    end
    return result
end

function NPCUtil.sameWorld(first, second)
    return isElement(first) and isElement(second)
        and getElementInterior(first) == getElementInterior(second)
        and getElementDimension(first) == getElementDimension(second)
end

function NPCUtil.arrayContains(array, value)
    for index = 1, #array do
        if array[index] == value then
            return true
        end
    end
    return false
end

function NPCUtil.tableCount(dictionary)
    local count = 0
    for _ in pairs(dictionary) do
        count = count + 1
    end
    return count
end
