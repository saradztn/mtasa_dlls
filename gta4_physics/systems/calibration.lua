GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.Calibration = { active = false, model = nil, references = {}, coefficients = {}, results = {}, runtime = {} }
local C = G4.Calibration

local function metricKey(value)
    local key = tostring(value or ""):lower():gsub("[^%w]", "")
    local aliases = {
        ["060"] = "zeroTo60", zero60 = "zeroTo60", zeroto60 = "zeroTo60",
        ["0100"] = "zeroTo100", zero100 = "zeroTo100", zeroto100 = "zeroTo100",
        topspeed = "topSpeed", vmax = "topSpeed", brakingdistance = "brakingDistance",
        cornering = "corneringG", corneringg = "corneringG", yawrate = "yawRate",
        rollrate = "rollRate", shifttime = "shiftTime"
    }
    return aliases[key]
end

function C.start(model)
    C.active = true
    C.model = tonumber(model)
    C.runtime = { startTick = getTickCount(), startSpeed = 0, distance = 0, braking = false, brakeDistance = 0,
        maxSpeed = 0, maxLateralG = 0, maxYawRate = 0, maxRollRate = 0, lastRoll = nil, lastTick = nil, shiftTimes = {}, lastGear = nil }
    return true
end

function C.update(state, dt)
    if not C.active or (C.model and C.model ~= state.model) then return end
    local r = C.runtime
    local speed = math.max(0, state.speedMps or 0)
    local now = getTickCount()
    r.distance = (r.distance or 0) + speed * dt
    r.maxSpeed = math.max(r.maxSpeed or 0, speed)
    r.maxLateralG = math.max(r.maxLateralG or 0, math.abs(state.lateralG or 0))
    r.maxYawRate = math.max(r.maxYawRate or 0, math.abs(state.yawRate or 0))
    if r.lastRoll and r.lastTick and dt > 0 then
        r.maxRollRate = math.max(r.maxRollRate or 0, math.abs((state.roll - r.lastRoll) / dt))
    end
    r.lastRoll, r.lastTick = state.roll, now
    if speed > 1 and not r.zeroStart then r.zeroStart = now end
    if r.zeroStart and not r.zeroTo60 and speed >= 60 / 3.6 then r.zeroTo60 = (now - r.zeroStart) / 1000 end
    if r.zeroStart and not r.zeroTo100 and speed >= 100 / 3.6 then r.zeroTo100 = (now - r.zeroStart) / 1000 end
    if state.brake and state.brake > 0.55 and speed > 4 then
        r.braking = true
        r.brakeDistance = (r.brakeDistance or 0) + speed * dt
    elseif r.braking then
        r.braking = false
        r.lastBrakingDistance = r.brakeDistance
        r.brakeDistance = 0
    end
    if r.lastGear and state.gear ~= r.lastGear and G4.isFinite(state.lastShiftDuration) and state.lastShiftDuration > 0 then
        r.shiftTimes[#r.shiftTimes + 1] = state.lastShiftDuration
    end
    r.lastGear = state.gear
    C.results[state.model] = {
        zeroTo60 = r.zeroTo60, zeroTo100 = r.zeroTo100, topSpeed = r.maxSpeed,
        brakingDistance = r.lastBrakingDistance, corneringG = r.maxLateralG,
        yawRate = r.maxYawRate, rollRate = r.maxRollRate,
        shiftTime = #r.shiftTimes > 0 and (function() local sum = 0 for _, v in ipairs(r.shiftTimes) do sum = sum + v end return sum / #r.shiftTimes end)() or nil
    }
end

function C.setReference(model, metric, value)
    model, value = tonumber(model), tonumber(value)
    metric = metricKey(metric)
    if not model or not G4.VehicleDatabase.get(model) or not metric or not G4.isFinite(value) or value <= 0 then
        return false, "invalid or unsupported model, metric, or value"
    end
    C.references[model] = C.references[model] or {}
    C.references[model][metric] = value
    return true
end

function C.compare(model)
    model = tonumber(model)
    local refs = model and (C.references[model] or C.references[tostring(model)]) or nil
    local measured = model and (C.results[model] or C.results[tostring(model)]) or nil
    if type(refs) ~= "table" or type(measured) ~= "table" then return nil, "No reference/result data for this model" end
    local report = {}
    for metric, reference in pairs(refs) do
        local actual = measured[metric]
        if G4.isFinite(reference) and G4.isFinite(actual) and reference ~= 0 then
            local errorPct = (actual - reference) / reference * 100
            report[metric] = { reference = reference, measured = actual, errorPct = errorPct }
            local coeffName, factor
            if (metric == "zeroTo60" or metric == "zeroTo100") and actual > 0 then
                coeffName, factor = "engine", actual / reference
            elseif metric == "topSpeed" and actual > 0 then
                coeffName, factor = "speed", reference / actual
            elseif metric == "brakingDistance" then
                coeffName, factor = "brake", actual / reference
            elseif metric == "corneringG" and actual > 0 then
                coeffName, factor = "tire", reference / actual
            elseif metric == "shiftTime" and actual > 0 then
                coeffName, factor = "shift", reference / actual
            end
            if coeffName and G4.isFinite(factor) then
                C.coefficients[model] = C.coefficients[model] or {}
                C.coefficients[model][coeffName] = M.clamp(factor, 0.78, 1.28)
            end
        end
    end
    return report
end

function C.getCoefficient(model, name)
    local id = tonumber(model)
    local row = id and (C.coefficients[id] or C.coefficients[tostring(id)]) or nil
    local value = row and tonumber(row[name]) or 1
    if not G4.isFinite(value) then return 1 end
    return M.clamp(value, 0.78, 1.28)
end

function C.save()
    if type(fileCreate) ~= "function" or type(toJSON) ~= "function" then return false end
    local handle = fileCreate("@gta4physics_calibration.json")
    if not handle then return false end
    local ok, encoded = pcall(toJSON, { references = C.references, coefficients = C.coefficients }, true)
    if ok and type(encoded) == "string" then fileWrite(handle, encoded) else fileClose(handle); return false end
    fileClose(handle)
    return true
end

function C.load()
    if type(fileExists) ~= "function" or not fileExists("@gta4physics_calibration.json") or type(fileOpen) ~= "function" then return false end
    local handle = fileOpen("@gta4physics_calibration.json", true)
    if not handle then return false end
    local size = fileGetSize(handle)
    local raw = fileRead(handle, size)
    fileClose(handle)
    if type(raw) ~= "string" or type(fromJSON) ~= "function" then return false end
    local ok, decoded = pcall(fromJSON, raw)
    if not ok or type(decoded) ~= "table" then return false end
    C.references = type(decoded.references) == "table" and decoded.references or {}
    C.coefficients = type(decoded.coefficients) == "table" and decoded.coefficients or {}
    return true
end
