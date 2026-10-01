GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.Collision = {}

function G4.Collision.estimate(spec, ownVelocity, otherVelocity, normal, otherMass, eventImpulse)
    local n = M.normalize(normal or { x = 0, y = 0, z = 0 }, { x = 0, y = 0, z = 1 })
    local relative = M.sub(ownVelocity or { x = 0, y = 0, z = 0 }, otherVelocity or { x = 0, y = 0, z = 0 })
    local closingSpeed = math.max(0, -M.dot(relative, n))
    local m1 = math.max(1, spec.mass or 1)
    local m2 = math.max(1, otherMass or m1 * 8)
    local reducedMass = m1 * m2 / (m1 + m2)
    local restitution = M.clamp(spec.collision and spec.collision.restitution or 0.1, 0, 0.35)
    local impulseNs = reducedMass * closingSpeed * (1 + restitution)
    if G4.isFinite(eventImpulse) and eventImpulse > 0 then
        impulseNs = math.max(impulseNs, math.min(eventImpulse * m1 * 0.02, m1 * 18))
    end
    return { closingSpeed = closingSpeed, reducedMass = reducedMass, impulseNs = impulseNs, normal = n,
        severity = M.clamp(impulseNs / math.max(m1 * 8, 1), 0, 1) }
end

function G4.Collision.onImpact(vehicle, hitElement, eventImpulse, collisionX, collisionY, collisionZ, normalX, normalY, normalZ)
    if not isElement(vehicle) then return false end
    local manager = G4.VehicleManager
    local state = manager and manager.states and manager.states[vehicle]
    local spec = G4.VehicleDatabase and G4.VehicleDatabase.get(getElementModel(vehicle))
    if not state or not spec then return false end
    local currentVelocity = G4.Adapter.getVelocityMps(vehicle)
    local otherVelocity = { x = 0, y = 0, z = 0 }
    local otherMass = spec.mass * 8
    if isElement(hitElement) and getElementType(hitElement) == "vehicle" then
        otherVelocity = G4.Adapter.getVelocityMps(hitElement)
        local handling = getVehicleHandling(hitElement)
        if handling and tonumber(handling.mass) then otherMass = handling.mass end
    end
    local result = G4.Collision.estimate(spec, currentVelocity, otherVelocity,
        { x = normalX or 0, y = normalY or 0, z = normalZ or 0 }, otherMass, eventImpulse)
    result.point = { x = collisionX or 0, y = collisionY or 0, z = collisionZ or 0 }
    state.lastCollision = result
    state.collisionTimeLeft = G4.Config.collisionQuietMs / 1000
    state.collisionYawDamping = 1 + result.severity * (spec.collision.yawDamping or 0.2)
    if G4.Telemetry then G4.Telemetry.mark("collision", result.severity) end
    return true
end
