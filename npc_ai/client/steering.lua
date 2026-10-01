-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: STEERING
-- ============================================================================

NPCSteering = NPCSteering or {}

local function nextPathTarget(agent, x, y, z)
    local path = agent.path
    if not path or not path.nodes then
        return nil, "no path"
    end

    while agent.path.index <= #path.nodes do
        local node = NPCNodes.getNode(path.nodes[agent.path.index])
        if not node then
            return nil, "path node streamed out"
        end

        local distance = NPCUtil.distance3D(x, y, z, node.x, node.y, node.z)
        if distance > Config.pathfinding.nodeArrivalDistance then
            return {
                x = node.x,
                y = node.y,
                z = node.z,
                node = node,
                kind = "node",
                distance = distance,
            }
        end

        agent.currentNode = node.id
        agent.path.index = agent.path.index + 1
        if NPCAI and NPCAI.onNodeReached then
            NPCAI.onNodeReached(agent, node)
        end
        if agent.path ~= path then
            return nil, "path invalidated"
        end
    end

    local finalNode = NPCNodes.getNode(path.nodes[#path.nodes])
    local destination = agent.destination
    if finalNode and destination and NPCGraph.canUseFinalApproach(finalNode, destination, agent.ped) then
        local distance = NPCUtil.distance3D(x, y, z, destination.x, destination.y, destination.z)
        if distance > Config.pathfinding.goalArrivalDistance then
            return {
                x = destination.x,
                y = destination.y,
                z = destination.z,
                node = finalNode,
                kind = "final",
                distance = distance,
            }
        end
    end

    return nil, "path complete"
end

function NPCSteering.compute(agent, deltaSeconds)
    local ped = agent.ped
    local x, y, z = getElementPosition(ped)

    if agent.recovery and agent.recovery.target then
        local target = agent.recovery.target
        local dx, dy = target.x - x, target.y - y
        local directionX, directionY, length = NPCUtil.normalize2D(dx, dy)
        if length > 0 then
            return {
                target = target,
                heading = NPCUtil.rotationFromVector(directionX, directionY),
                directionX = directionX,
                directionY = directionY,
                speedFactor = 0.52,
                targetSpeed = Config.movement.walkSpeed * 0.55,
                recovering = true,
            }
        end
    end

    local target, reason = nextPathTarget(agent, x, y, z)
    if not target then
        return nil, reason
    end

    local desiredX, desiredY = NPCUtil.normalize2D(target.x - x, target.y - y)
    local avoidance = agent.avoidance or {}
    local forceX = avoidance.forceX or 0
    local forceY = avoidance.forceY or 0
    local steeringX, steeringY = NPCUtil.normalize2D(desiredX + forceX, desiredY + forceY)
    if steeringX == 0 and steeringY == 0 then
        steeringX, steeringY = desiredX, desiredY
    end

    local heading = NPCUtil.rotationFromVector(steeringX, steeringY)
    local _, _, currentRotation = getElementRotation(ped)
    local turn = math.abs(NPCUtil.angleDifference(currentRotation, heading))
    local speedFactor = 1

    if turn >= Config.movement.turnStopAt then
        speedFactor = 0.18
    elseif turn > Config.movement.turnSlowdownStart then
        local span = Config.movement.turnStopAt - Config.movement.turnSlowdownStart
        local turnRatio = (turn - Config.movement.turnSlowdownStart) / span
        speedFactor = 1 - 0.72 * turnRatio
    end

    if target.distance < 3.0 then
        speedFactor = math.min(speedFactor, NPCUtil.clamp(target.distance / 3.0, 0.22, 1))
    end
    speedFactor = speedFactor * (avoidance.speedFactor or 1)

    return {
        target = target,
        heading = heading,
        directionX = steeringX,
        directionY = steeringY,
        speedFactor = NPCUtil.clamp(speedFactor, 0, 1),
        targetSpeed = agent.speed or Config.movement.defaultSpeed,
        recovering = false,
    }
end
