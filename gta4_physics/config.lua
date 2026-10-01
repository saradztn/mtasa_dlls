GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics

G4.VERSION = "0.1.0"

-- Tuning knobs (all values live here so no physics constant is hard-coded in
-- physics_core.lua):
--   fixedStep / maxSubsteps / maxFrameDelta : fixed-step budget
--   customForceBlend      : share of the modelled longitudinal/lateral force
--                           applied as a velocity correction (0.28 = 28%)
--   customAngularBlend    : share of the reference body roll/pitch attitude this
--                           layer contributes (0.10 -> ~35% of the reference
--                           angle; 0.30 -> up to 100%)
--   handling.*            : how strongly the estimated MTA handling base is
--                           blended toward the database values, and how much the
--                           native engine/grip/brake strength is attenuated so
--                           the custom model is not fighting the native solver
--   suspension.*          : body-moment blend, optional vertical correction and
--                           the per-second cap on commanded body rates
--   profiles.*            : per-profile multipliers for tire, brake, steering,
--                           engine, suspension and force (never edits the DB)
G4.Config = {
    enabledByDefault = true, defaultProfile = "gta4", fixedStep = 1 / 60, maxFrameDelta = 0.05, maxSubsteps = 3,
    maxCustomAcceleration = 7.0, customForceBlend = 0.28, customAngularBlend = 0.10,
    maxAngularCorrection = 0.42, velocityCorrectionRate = 1.35, surfaceSampleMs = 220,
    lodUpdateMs = 450, telemetrySampleMs = 80, syncIntervalMs = 120, syncRateLimitMs = 80, syncRange = 150,
    nearRange = 48, farRange = 155, collisionQuietMs = 260, maxTelemetrySamples = 7200,
    handling = { massBlend = 0.72, otherNumericBlend = 0.46, nativeEngineScale = 0.62, nativeGripScale = 0.86, nativeBrakeScale = 0.84, restoreOnExit = true },
    suspension = { bodyMomentBlend = 0.10, verticalCorrection = 0.10, maxBodyRate = 0.55 },
    network = { enabled = true, maxReportedSpeed = 130, maxReportedRPM = 16000, maxReportedSlip = 8, maxCorrectionMps = 2.2, stateExpiryMs = 1500 },
    profiles = {
        gta4 = { label = "GTA IV STYLE", tire = 1.00, brake = 1.00, steering = 1.00, engine = 1.00, suspension = 1.00, force = 1.00 },
        comfort = { label = "COMFORT", tire = 0.96, brake = 0.96, steering = 0.88, engine = 0.92, suspension = 0.82, force = 0.85 },
        sport = { label = "SPORT", tire = 1.03, brake = 1.04, steering = 1.08, engine = 1.06, suspension = 1.12, force = 1.05 },
        drift = { label = "DRIFT", tire = 0.91, brake = 0.94, steering = 1.12, engine = 1.02, suspension = 0.96, force = 0.95 }
    },
    commands = { physics = "gta4physics", debug = "gta4debug", reset = "gta4reset", profile = "gta4profile", reload = "gta4reload", telemetry = "gta4telemetry", calibrate = "gta4calibrate" },
    eventNames = { state = "gta4physics:state", ack = "gta4physics:ack" }
}
G4.State = { enabled = G4.Config.enabledByDefault, debug = false, debugFull = false, profile = G4.Config.defaultProfile, activeVehicle = nil, activeModel = nil, resourceStarted = false }

function G4.copyTable(value, seen)
    if type(value) ~= "table" then return value end
    seen = seen or {}
    if seen[value] then return seen[value] end
    local result = {}
    seen[value] = result
    for key, item in pairs(value) do result[G4.copyTable(key, seen)] = G4.copyTable(item, seen) end
    return result
end
function G4.isFinite(value)
    return type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end
function G4.safeNumber(value, fallback)
    if G4.isFinite(value) then return value end
    return fallback or 0
end
function G4.log(message, level)
    outputDebugString("[GTA4P " .. G4.VERSION .. "] " .. tostring(message), level or 3, 128, 212, 250)
end
function G4.notify(message, r, g, b)
    outputChatBox("[GTA4P] " .. tostring(message), r or 125, g or 210, b or 255, false)
end
