GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
G4.Commands = { started = false }

local function help()
    G4.notify("/gta4physics on|off|status | /gta4debug on|off|full | /gta4reset | /gta4profile gta4|comfort|sport|drift")
    G4.notify("/gta4reload | /gta4telemetry start|stop|csv|json|clear | /gta4calibrate start|stop|ref <metric> <value>|compare")
end

local function physicsCommand(_, action)
    action = tostring(action or "status"):lower()
    if action == "on" then G4.VehicleManager.setEnabled(true)
    elseif action == "off" then G4.VehicleManager.setEnabled(false)
    elseif action == "toggle" then G4.VehicleManager.setEnabled(not G4.State.enabled)
    elseif action == "status" then
        local vehicle = G4.VehicleManager.activeVehicle
        local state = vehicle and G4.VehicleManager.states[vehicle]
        if not state then G4.notify("No supported driver vehicle. Native MTA solver remains active.")
        else
            G4.notify(string.format("%s | %s | %.1f km/h | %d RPM | gear %d | %s LOD | %d estimated entries",
                G4.State.enabled and "ON" or "OFF", G4.Config.profiles[G4.State.profile].label,
                state.speedKmh or 0, math.floor(state.rpm or 0), state.gear or 0,
                G4.Performance.getLod(vehicle), G4.VehicleDatabase.count()))
        end
    else help() end
end

local function debugCommand(_, mode)
    mode = tostring(mode or "on"):lower()
    if mode == "off" then G4.State.debug, G4.State.debugFull = false, false
    elseif mode == "full" then G4.State.debug, G4.State.debugFull = true, true
    elseif mode == "on" or mode == "basic" then G4.State.debug, G4.State.debugFull = true, false
    else G4.notify("Use /gta4debug on, off or full."); return end
    G4.notify("Physics telemetry " .. (G4.State.debug and (G4.State.debugFull and "and force vectors enabled." or "enabled.") or "disabled."))
end

local function resetCommand()
    if not G4.VehicleManager.resetCurrent() then G4.notify("Enter a supported vehicle as driver first.") end
end

local function profileCommand(_, profile)
    if not profile or not G4.VehicleManager.setProfile(profile) then
        G4.notify("Profiles: gta4, comfort, sport, drift.", 255, 190, 120)
    end
end

local function reloadCommand()
    if G4.VehicleManager.reloadCurrent() then G4.notify("Loaded database coefficients reapplied; original estimated entries remain unchanged.")
    else G4.notify("No supported driver vehicle to reload.", 255, 190, 120) end
end

local function telemetryCommand(_, action, format)
    action = tostring(action or "start"):lower()
    if action == "start" then G4.Telemetry.start(); G4.notify("Telemetry recording started (local ring buffer).")
    elseif action == "stop" then G4.Telemetry.stop(); G4.notify("Telemetry recording stopped; use /gta4telemetry csv|json to export.")
    elseif action == "csv" or action == "json" then
        G4.Telemetry.stop()
        local ok, result = G4.Telemetry.export(action)
        G4.notify(ok and ("Telemetry written to " .. result) or ("Telemetry export failed: " .. tostring(result)), ok and 130 or 255, ok and 220 or 150, ok and 255 or 120)
    elseif action == "clear" then G4.Telemetry.clear(); G4.notify("Telemetry buffer cleared.")
    else G4.notify("Use /gta4telemetry start|stop|csv|json|clear.") end
end

local function calibrateCommand(_, action, metric, value)
    action = tostring(action or "help"):lower()
    local model = G4.State.activeModel
    if action == "start" then
        if not model then G4.notify("Enter a supported vehicle first."); return end
        G4.Calibration.start(model)
        G4.Telemetry.start()
        G4.notify("Calibration run started. Accelerate from rest, brake, corner, then use compare.")
    elseif action == "stop" then
        G4.Calibration.active = false
        G4.Telemetry.stop()
        G4.Calibration.save()
        G4.notify("Calibration run stopped and coefficients saved separately from the vehicle database.")
    elseif action == "ref" then
        if not model or not metric or not value then G4.notify("Syntax: /gta4calibrate ref <0-60|0-100|topSpeed|brakingDistance|corneringG|yawRate|rollRate|shiftTime> <reference>"); return end
        local ok, err = G4.Calibration.setReference(model, metric, tonumber(value))
        if not ok then G4.notify("Reference rejected: " .. tostring(err), 255, 150, 120); return end
        G4.Calibration.save()
        G4.notify("Reference stored for model " .. model .. "; original vehicle estimate not modified.")
    elseif action == "compare" then
        if not model then G4.notify("Enter a supported vehicle first."); return end
        local report, err = G4.Calibration.compare(model)
        if not report then G4.notify(err, 255, 150, 120); return end
        local printed = false
        for name, result in pairs(report) do
            G4.notify(string.format("%s: measured %.3f / reference %.3f | error %+.1f%%", name, result.measured, result.reference, result.errorPct))
            printed = true
        end
        if not printed then G4.notify("No comparable reference metrics. Add a reference and run calibration first.") end
        G4.Calibration.save()
    elseif action == "clear" then
        if model then G4.Calibration.references[model] = nil; G4.Calibration.coefficients[model] = nil; G4.Calibration.results[model] = nil end
        G4.Calibration.save()
        G4.notify("Current-model calibration data cleared; source database unchanged.")
    else
        G4.notify("Calibration: /gta4calibrate start | stop | ref <metric> <value> | compare | clear")
    end
end

function G4.Commands.start()
    if G4.Commands.started then return end
    G4.Commands.started = true
    addCommandHandler(G4.Config.commands.physics, physicsCommand)
    addCommandHandler(G4.Config.commands.debug, debugCommand)
    addCommandHandler(G4.Config.commands.reset, resetCommand)
    addCommandHandler(G4.Config.commands.profile, profileCommand)
    addCommandHandler(G4.Config.commands.reload, reloadCommand)
    addCommandHandler(G4.Config.commands.telemetry, telemetryCommand)
    addCommandHandler(G4.Config.commands.calibrate, calibrateCommand)
    addCommandHandler("gta4help", help)
end

function G4.Commands.stop()
    if not G4.Commands.started then return end
    for _, name in pairs(G4.Config.commands) do removeCommandHandler(name) end
    removeCommandHandler("gta4help")
    G4.Commands.started = false
end
