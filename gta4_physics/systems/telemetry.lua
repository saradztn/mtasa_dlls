GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.Telemetry = { active = false, samples = {}, lastSampleTick = 0, marks = {}, filePrefix = "@gta4physics_telemetry" }
local T = G4.Telemetry

local function rounded(value, places)
    local scale = 10 ^ (places or 3)
    return math.floor((tonumber(value) or 0) * scale + 0.5) / scale
end

function T.start()
    T.active = true
    T.lastSampleTick = 0
    T.samples = {}
    T.marks = {}
    return true
end
function T.stop() T.active = false return true end
function T.clear() T.samples, T.marks = {}, {} end
function T.mark(name, value)
    T.marks[#T.marks + 1] = { tick = getTickCount(), name = tostring(name or "mark"), value = rounded(value, 3) }
    if #T.marks > 500 then table.remove(T.marks, 1) end
end

function T.update(state, dt)
    if not T.active or type(state) ~= "table" then return end
    local now = getTickCount()
    if now - T.lastSampleTick < G4.Config.telemetrySampleMs then return end
    T.lastSampleTick = now
    local wheels = state.tireWheels or {}
    local sample = {
        tick = now, speed_mps = rounded(state.speedMps, 3), speed_kmh = rounded(state.speedKmh, 2),
        rpm = rounded(state.rpm, 0), gear = tonumber(state.gear) or 0,
        throttle = rounded(state.throttle, 3), brake = rounded(state.brake, 3), steering = rounded(state.steering, 3),
        yaw_rate_rad_s = rounded(state.yawRate, 4), pitch_deg = rounded(state.pitch, 3), roll_deg = rounded(state.roll, 3),
        longitudinal_g = rounded(state.longitudinalG, 3), lateral_g = rounded(state.lateralG, 3), surface = tostring(state.surfaceName or "unknown"),
        fl_slip = rounded(wheels.FL and wheels.FL.combinedSlip, 3), fr_slip = rounded(wheels.FR and wheels.FR.combinedSlip, 3),
        rl_slip = rounded(wheels.RL and wheels.RL.combinedSlip, 3), rr_slip = rounded(wheels.RR and wheels.RR.combinedSlip, 3),
        fl_load = rounded(wheels.FL and wheels.FL.wheelLoad, 1), fr_load = rounded(wheels.FR and wheels.FR.wheelLoad, 1),
        rl_load = rounded(wheels.RL and wheels.RL.wheelLoad, 1), rr_load = rounded(wheels.RR and wheels.RR.wheelLoad, 1)
    }
    T.samples[#T.samples + 1] = sample
    while #T.samples > G4.Config.maxTelemetrySamples do table.remove(T.samples, 1) end
end

local csvColumns = {
    "tick", "speed_mps", "speed_kmh", "rpm", "gear", "throttle", "brake", "steering",
    "yaw_rate_rad_s", "pitch_deg", "roll_deg", "longitudinal_g", "lateral_g", "surface",
    "fl_slip", "fr_slip", "rl_slip", "rr_slip", "fl_load", "fr_load", "rl_load", "rr_load"
}

function T.export(format)
    format = tostring(format or "csv"):lower()
    if type(fileCreate) ~= "function" or type(fileWrite) ~= "function" then return false, "MTA file API unavailable" end
    local path = T.filePrefix .. (format == "json" and ".json" or ".csv")
    local handle = fileCreate(path)
    if not handle then return false, "Could not create " .. path end
    local ok, err = pcall(function()
        if format == "json" then
            local json
            if type(toJSON) == "function" then json = toJSON({ samples = T.samples, marks = T.marks }, true) end
            if type(json) ~= "string" then error("JSON encoder unavailable") end
            fileWrite(handle, json)
        else
            fileWrite(handle, table.concat(csvColumns, ",") .. "\n")
            for _, row in ipairs(T.samples) do
                local values = {}
                for index, column in ipairs(csvColumns) do
                    local value = tostring(row[column] or "")
                    if value:find('[,"\n]') then value = '"' .. value:gsub('"', '""') .. '"' end
                    values[index] = value
                end
                fileWrite(handle, table.concat(values, ",") .. "\n")
            end
        end
    end)
    fileClose(handle)
    if not ok then return false, tostring(err) end
    return true, path
end

function T.getSampleCount() return #T.samples end
