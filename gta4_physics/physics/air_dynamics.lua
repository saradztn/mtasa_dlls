GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.AirDynamics = {}

function G4.AirDynamics.compute(spec, velocity, profile)
    local speed = M.length(velocity)
    local rho = 1.225
    local aero = spec.aero or {}
    local dragArea = math.max(0, aero.dragArea or spec.drag or 0.7)
    local speedCoefficient = G4.Calibration and G4.Calibration.getCoefficient and G4.Calibration.getCoefficient(spec.model, "speed") or 1
    local dragForce = 0.5 * rho * dragArea * speed * speed / math.max(0.65, speedCoefficient)
    local direction = speed > 0.01 and M.scale(velocity, -1 / speed) or { x = 0, y = 0, z = 0 }
    local drag = M.scale(direction, dragForce)
    local downArea = math.max(0, aero.downforceArea or 0)
    local liftArea = aero.liftArea or 0
    local downforce = 0.5 * rho * downArea * speed * speed
    local lift = 0.5 * rho * liftArea * speed * speed
    local limit = math.max(0, spec.mass * 9.81 * (aero.downforceLimitG or 0.2))
    downforce = M.clamp(downforce, 0, limit)
    lift = M.clamp(lift, -limit * 0.25, limit * 0.35)
    local scale = (profile and profile.force) or 1
    return { force = M.scale(drag, scale), downforce = downforce * scale, lift = lift * scale, speed = speed }
end
