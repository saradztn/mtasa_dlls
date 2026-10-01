-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: MOVEMENT ANIMATION SYNCHRONIZATION
-- ============================================================================

NPCAnimation = NPCAnimation or {}

function NPCAnimation.update(agent, normalizedSpeed)
    local ped = agent.ped
    if not isElement(ped) then
        return
    end

    normalizedSpeed = NPCUtil.clamp(normalizedSpeed or 0, 0, 1)
    local desiredRate = Config.movement.animationMinRate
        + (Config.movement.animationMaxRate - Config.movement.animationMinRate) * normalizedSpeed

    if normalizedSpeed <= 0.02 then
        desiredRate = Config.movement.animationMinRate
    end

    if agent.lastAnimationRate and math.abs(agent.lastAnimationRate - desiredRate) < 0.06 then
        return
    end

    -- Ped controls drive GTA's native locomotion animation.  We only adjust
    -- the currently active animation rate instead of forcing a root-motion
    -- animation that could bypass collision or desynchronise position.
    local _, animation = getPedAnimation(ped)
    if animation then
        setPedAnimationSpeed(ped, animation, desiredRate)
    end
    agent.lastAnimationRate = desiredRate
end
