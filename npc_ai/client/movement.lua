-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: PED CONTROL MOVEMENT
-- ============================================================================

NPCMovement = NPCMovement or {}

local controlledStates = { "forwards", "backwards", "left", "right", "walk", "sprint" }

local function setControl(agent, control, state)
    agent.controls = agent.controls or {}
    if agent.controls[control] == state then
        return
    end
    setPedControlState(agent.ped, control, state)
    agent.controls[control] = state
end

function NPCMovement.release(agent)
    if not agent or not isElement(agent.ped) then
        return
    end
    agent.controls = agent.controls or {}
    for index = 1, #controlledStates do
        setControl(agent, controlledStates[index], false)
    end
    agent.currentSpeed = 0
end

function NPCMovement.apply(agent, intent, deltaSeconds)
    local ped = agent.ped
    if not isElement(ped) then
        return
    end

    if not isElementSyncer(ped) then
        NPCMovement.release(agent)
        return
    end

    if not intent then
        NPCMovement.release(agent)
        NPCAnimation.update(agent, 0)
        return
    end

    deltaSeconds = NPCUtil.clamp(deltaSeconds or 0.05, 0.01, 0.25)
    local targetSpeed = intent.targetSpeed * intent.speedFactor
    local currentSpeed = agent.currentSpeed or 0
    local rate = targetSpeed > currentSpeed and Config.movement.acceleration or Config.movement.deceleration
    local step = rate * deltaSeconds
    if math.abs(targetSpeed - currentSpeed) <= step then
        currentSpeed = targetSpeed
    elseif targetSpeed > currentSpeed then
        currentSpeed = currentSpeed + step
    else
        currentSpeed = currentSpeed - step
    end
    agent.currentSpeed = math.max(0, currentSpeed)

    local _, _, currentRotation = getElementRotation(ped)
    local rotationStep = Config.movement.maxTurnDegreesPerSecond * deltaSeconds
    local interpolatedRotation = NPCUtil.approachAngle(currentRotation, intent.heading, rotationStep)
    local angleError = NPCUtil.angleDifference(currentRotation, intent.heading)

    -- This is rotation interpolation at the scheduled AI rate (not a direct
    -- target rotation every render frame). Position is exclusively driven by
    -- native ped controls and GTA collision; setElementPosition is never used.
    if math.abs(NPCUtil.angleDifference(currentRotation, interpolatedRotation)) >= Config.movement.rotationEpsilon then
        setElementRotation(ped, 0, 0, interpolatedRotation, "default", true)
    end

    local moving = agent.currentSpeed > 0.08 and math.abs(angleError) < Config.movement.turnStopAt
    setControl(agent, "forwards", moving)
    setControl(agent, "backwards", false)

    local useSprint = Config.movement.allowRun and agent.currentSpeed >= Config.movement.fastWalkSpeed
    setControl(agent, "sprint", useSprint)
    setControl(agent, "walk", moving and not useSprint)

    -- Ped turn controls retain natural task/animation behaviour on sharp
    -- corners; the interpolated heading keeps their desired facing stable.
    setControl(agent, "left", moving and angleError < -Config.movement.turnControlThreshold)
    setControl(agent, "right", moving and angleError > Config.movement.turnControlThreshold)

    local speedScale = Config.movement.runSpeed > 0 and agent.currentSpeed / Config.movement.runSpeed or 0
    NPCAnimation.update(agent, speedScale)
end
