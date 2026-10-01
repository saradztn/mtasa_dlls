-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: LOCAL OBSTACLE AND WALL AVOIDANCE
-- ============================================================================

NPCAvoidance = NPCAvoidance or {}

local function addForce(result, x, y, strength)
    result.forceX = result.forceX + x * strength
    result.forceY = result.forceY + y * strength
end

local function castRay(agent, result, name, heading, length)
    local ped = agent.ped
    local x, y, z = getElementPosition(ped)
    local directionX, directionY = NPCUtil.vectorFromRotation(heading)
    local startX, startY, startZ = x, y, z + Config.avoidance.rayStartHeight
    local endX = startX + directionX * length
    local endY = startY + directionY * length
    local endZ = startZ

    local hit, hitX, hitY, hitZ, hitElement, normalX, normalY = processLineOfSight(
        startX, startY, startZ,
        endX, endY, endZ,
        true,  -- buildings
        true,  -- vehicles
        true,  -- players
        true,  -- objects
        false, -- dummies
        false,
        false,
        false,
        ped
    )

    local ray = {
        name = name,
        startX = startX,
        startY = startY,
        startZ = startZ,
        endX = endX,
        endY = endY,
        endZ = endZ,
        hit = hit == true,
        hitX = hitX,
        hitY = hitY,
        hitZ = hitZ,
        hitElement = hitElement,
    }
    result.rays[#result.rays + 1] = ray

    if not hit then
        return
    end

    local hitDistance = NPCUtil.distance3D(startX, startY, startZ, hitX, hitY, hitZ)
    local proximity = NPCUtil.clamp(1 - hitDistance / length, 0, 1)
    ray.distance = hitDistance
    ray.proximity = proximity

    local awayX, awayY = normalX or 0, normalY or 0
    awayX, awayY = NPCUtil.normalize2D(awayX, awayY)
    if awayX == 0 and awayY == 0 then
        awayX, awayY = -directionX, -directionY
    end
    addForce(result, awayX, awayY, proximity * Config.avoidance.wallWeight)

    if hitDistance < result.closestHitDistance then
        result.closestHitDistance = hitDistance
        result.closestHit = ray
    end
end

local function applyDynamicSeparation(agent, result)
    local ped = agent.ped
    local x, y, z = getElementPosition(ped)
    local range = Config.avoidance.dynamicRange
    local interior = getElementInterior(ped)
    local dimension = getElementDimension(ped)
    local types = { "ped", "vehicle" }

    for typeIndex = 1, #types do
        local elements = getElementsWithinRange(x, y, z, range, types[typeIndex], interior, dimension)
        if elements then
            for index = 1, #elements do
                local element = elements[index]
                if element ~= ped and isElement(element) then
                    local otherX, otherY, otherZ = getElementPosition(element)
                    local awayX, awayY, distance = NPCUtil.normalize2D(x - otherX, y - otherY)
                    if distance > 0.05 and distance < range then
                        local strength = ((range - distance) / range) * Config.avoidance.dynamicWeight
                        if getElementType(element) == "vehicle" then
                            strength = strength * 1.35
                        end
                        addForce(result, awayX, awayY, strength)
                        if distance < result.closestDynamicDistance then
                            result.closestDynamicDistance = distance
                        end
                    end
                end
            end
        end
    end
end

function NPCAvoidance.clear(agent)
    agent.avoidance = {
        forceX = 0,
        forceY = 0,
        speedFactor = 1,
        rays = {},
        closestHitDistance = math.huge,
        closestDynamicDistance = math.huge,
        blocked = false,
    }
end

function NPCAvoidance.update(agent, desiredHeading)
    if not Config.avoidance.enabled or agent.avoidanceEnabled == false then
        NPCAvoidance.clear(agent)
        return agent.avoidance
    end

    local timer = NPCProfiler.begin("avoidance")
    local result = {
        forceX = 0,
        forceY = 0,
        speedFactor = 1,
        rays = {},
        closestHitDistance = math.huge,
        closestDynamicDistance = math.huge,
        blocked = false,
    }

    castRay(agent, result, "forward", desiredHeading, Config.avoidance.rayLength)
    castRay(agent, result, "forward-left", desiredHeading + Config.avoidance.forwardLeftAngle, Config.avoidance.rayLength)
    castRay(agent, result, "forward-right", desiredHeading + Config.avoidance.forwardRightAngle, Config.avoidance.rayLength)
    castRay(agent, result, "left", desiredHeading + Config.avoidance.sideAngle, Config.avoidance.sideRayLength)
    castRay(agent, result, "right", desiredHeading - Config.avoidance.sideAngle, Config.avoidance.sideRayLength)
    applyDynamicSeparation(agent, result)

    result.forceX, result.forceY, result.forceLength = NPCUtil.normalize2D(result.forceX, result.forceY)
    result.forceX = result.forceX * math.min(result.forceLength, Config.avoidance.maximumForce)
    result.forceY = result.forceY * math.min(result.forceLength, Config.avoidance.maximumForce)

    local closest = math.min(result.closestHitDistance, result.closestDynamicDistance)
    if closest < Config.avoidance.slowDistance then
        result.speedFactor = NPCUtil.clamp(closest / Config.avoidance.slowDistance, 0.16, 1)
    end
    result.blocked = closest <= Config.avoidance.majorObstacleDistance

    local now = NPCUtil.now()
    if result.blocked then
        agent.blockedSince = agent.blockedSince or now
    else
        agent.blockedSince = nil
    end

    agent.avoidance = result
    NPCProfiler.finish(timer)
    return result
end

function NPCAvoidance.getIntervalForLOD(lod)
    if lod == "near" then
        return Config.avoidance.nearIntervalMs
    elseif lod == "medium" then
        return Config.avoidance.mediumIntervalMs
    end
    return Config.avoidance.farIntervalMs
end
