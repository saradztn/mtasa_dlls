GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.Visualizer = {}

local function fmt(value, places)
    return string.format("%.*f", places or 1, tonumber(value) or 0)
end

local function drawVector(vehicle, state)
    if not state or not state.tireWheels or not isElement(vehicle) or type(dxDrawLine3D) ~= "function" then return end
    local basis = G4.Adapter.getBasis(vehicle)
    local spec = state.spec
    local center = basis.position
    local positions = {
        FL = { x = -spec.dimensions.trackWidth * 0.5, y = spec.dimensions.wheelbase * 0.5 },
        FR = { x = spec.dimensions.trackWidth * 0.5, y = spec.dimensions.wheelbase * 0.5 },
        RL = { x = -spec.dimensions.trackWidth * 0.5, y = -spec.dimensions.wheelbase * 0.5 },
        RR = { x = spec.dimensions.trackWidth * 0.5, y = -spec.dimensions.wheelbase * 0.5 }
    }
    if spec.class == "motorcycle" then positions.FL.x, positions.RL.x = 0, 0 end
    for name, localPos in pairs(positions) do
        local wheel = state.tireWheels[name]
        if wheel and (spec.class ~= "motorcycle" or name == "FL" or name == "RL") then
            local world = {
                x = center.x + basis.right.x * localPos.x + basis.forward.x * localPos.y - basis.up.x * 0.35,
                y = center.y + basis.right.y * localPos.x + basis.forward.y * localPos.y - basis.up.y * 0.35,
                z = center.z + basis.right.z * localPos.x + basis.forward.z * localPos.y - basis.up.z * 0.35
            }
            local loadRatio = M.clamp((wheel.wheelLoad or 0) / math.max(1, spec.mass * 9.81 / 4), 0, 1.8)
            local color = tocolor(80 + math.floor(120 * loadRatio), 220 - math.floor(95 * loadRatio), 60, 235)
            local endPoint = {
                x = world.x + basis.right.x * (wheel.fx or 0) / 18000 + basis.forward.x * (wheel.fy or 0) / 18000,
                y = world.y + basis.right.y * (wheel.fx or 0) / 18000 + basis.forward.y * (wheel.fy or 0) / 18000,
                z = world.z + basis.right.z * (wheel.fx or 0) / 18000 + basis.forward.z * (wheel.fy or 0) / 18000
            }
            dxDrawLine3D(world.x, world.y, world.z, endPoint.x, endPoint.y, endPoint.z, color, 2, false)
            local sx, sy = getScreenFromWorldPosition(world.x, world.y, world.z, 0.05, false)
            if sx and sy then dxDrawRectangle(sx - 3, sy - 3, 6, 6, color, false) end
        end
    end
end

function G4.Visualizer.render()
    if not G4.State.debug then return end
    local vehicle = G4.VehicleManager and G4.VehicleManager.activeVehicle
    local state = vehicle and G4.VehicleManager.states[vehicle]
    if not state then
        dxDrawText("GTA IV STYLE PHYSICS | Enter an estimated road vehicle as driver", 18, 18, 760, 42, tocolor(255, 218, 128, 240), 1, "default-bold", "left", "top", false, false, false, true)
        return
    end

    local stats = G4.Performance.getStats()
    local wheels = state.tireWheels or {}
    local loads = state.loads or {}
    local rows = {
        string.format("GTA IV STYLE EMULATOR | %s [%d] | %s LOD | %s", state.spec.name, state.model, stats.activeLod, G4.Config.profiles[state.profile].label),
        string.format("%.1f km/h | %d RPM | gear %d | throttle %.2f | brake %.2f | steer %.2f | ABS %s",
            state.speedKmh or 0, math.floor(state.rpm or 0), state.gear or 0, state.throttle or 0, state.brake or 0,
            state.steering or 0, state.absActive and "ACTIVE" or "off"),
        string.format("surface %s | aLong %+.2f g | aLat %+.2f g | yaw %+.2f rad/s | pitch %+.1f | roll %+.1f",
            tostring(state.surfaceName), state.longitudinalG or 0, state.lateralG or 0, state.yawRate or 0, state.pitch or 0, state.roll or 0),
        string.format("FL slip %+.2f / load %.0f N | FR slip %+.2f / load %.0f N",
            wheels.FL and wheels.FL.combinedSlip or 0, loads.FL or 0, wheels.FR and wheels.FR.combinedSlip or 0, loads.FR or 0),
        string.format("RL slip %+.2f / load %.0f N | RR slip %+.2f / load %.0f N",
            wheels.RL and wheels.RL.combinedSlip or 0, loads.RL or 0, wheels.RR and wheels.RR.combinedSlip or 0, loads.RR or 0),
        string.format("step %.3f ms avg | near %d | far %d | network correction smooth / no position snap",
            stats.averageStepMs or 0, stats.lods.NEAR or 0, stats.lods.FAR or 0)
    }
    local x, y, width = 18, 18, 560
    local height = #rows * 19 + 14
    dxDrawRectangle(x, y, width, height, tocolor(5, 9, 14, 218), false)
    dxDrawRectangle(x, y, 3, height, tocolor(33, 177, 222, 255), false)
    for index, row in ipairs(rows) do
        dxDrawText(row, x + 12, y + 5 + (index - 1) * 19, x + width - 8, y + 21 + (index - 1) * 19,
            index == 1 and tocolor(102, 220, 255, 255) or tocolor(233, 238, 241, 245), 1, "default-bold", "left", "center", true, false, false, true)
    end
    if G4.State.debugFull then drawVector(vehicle, state) end
end
