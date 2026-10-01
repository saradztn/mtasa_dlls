GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.WeightTransfer = {}

function G4.WeightTransfer.compute(spec, longitudinalAcceleration, lateralAcceleration, downforce, contacts)
    local mass = math.max(1, spec.mass or 1)
    local dims, suspension = spec.dimensions, spec.suspension
    local wheelbase = math.max(0.5, dims.wheelbase or 2.5)
    local track = math.max(0.35, dims.trackWidth or 1.5)
    local cgHeight = math.max(0.15, dims.cgHeight or 0.5)
    local totalNormal = math.max(mass * 9.81 * 0.35, mass * 9.81 + (downforce or 0))
    local frontBias = M.clamp(dims.frontWeightBias or 0.55, 0.25, 0.75)
    local frontAxle = totalNormal * frontBias
    local rearAxle = totalNormal - frontAxle
    local longitudinalTransfer = mass * M.clamp(longitudinalAcceleration or 0, -14, 14) * cgHeight / wheelbase
    frontAxle, rearAxle = frontAxle - longitudinalTransfer, rearAxle + longitudinalTransfer
    local totalLateralTransfer = mass * M.clamp(lateralAcceleration or 0, -14, 14) * cgHeight / track
    local frontShare = M.clamp(suspension.bias or 0.53, 0.30, 0.72)
    local frontSideTransfer = totalLateralTransfer * frontShare * 0.5
    local rearSideTransfer = totalLateralTransfer * (1 - frontShare) * 0.5
    local loads
    if spec.class == "motorcycle" then
        -- The motorcycle model has one contact point per axle, not two half-loads.
        loads = { FL = math.max(0, frontAxle), FR = 0, RL = math.max(0, rearAxle), RR = 0 }
    else
        loads = {
            FL = math.max(0, frontAxle * 0.5 + frontSideTransfer),
            FR = math.max(0, frontAxle * 0.5 - frontSideTransfer),
            RL = math.max(0, rearAxle * 0.5 + rearSideTransfer),
            RR = math.max(0, rearAxle * 0.5 - rearSideTransfer)
        }
    end
    if contacts then
        for name, onGround in pairs(contacts) do if not onGround and loads[name] then loads[name] = 0 end end
    end
    if spec.class == "motorcycle" then loads.FR, loads.RR = 0, 0 end
    return { wheels = loads, longitudinalTransfer = longitudinalTransfer,
        lateralTransfer = totalLateralTransfer, totalNormal = loads.FL + loads.FR + loads.RL + loads.RR }
end
