local AR = AdvancedRendering

local presetAliases = {
    ultra = "ULTRA QUALITY",
    ultra_quality = "ULTRA QUALITY",
    high = "HIGH",
    cinematic = "CINEMATIC",
    realistic = "REALISTIC",
    balanced = "BALANCED",
    performance = "PERFORMANCE"
}

local featureAliases = {
    superresolution = "superResolution",
    shadowenhancement = "shadowEnhancement",
    vehicleresponse = "vehicleResponse",
    materialenhancement = "materialEnhancement",
    tonemapping = "toneMapping",
    autoexposure = "autoExposure",
    colormanagement = "colorManagement"
}

local function normalizePreset(name)
    local value = string.upper(tostring(name or "")):gsub("%s+", "_")
    if presetAliases[string.lower(tostring(name or ""))] then
        return presetAliases[string.lower(tostring(name or ""))]
    end
    if value == "ULTRA_QUALITY" then
        return "ULTRA QUALITY"
    end
    return value:gsub("_", " ")
end

function AR.applyPreset(name)
    local key = normalizePreset(name)
    local preset = AR.Presets[key]
    if not preset then
        AR.notify("Unknown preset. Use ultra, high, cinematic, realistic, balanced or performance.", 255, 190, 120)
        return false
    end

    AR.State.preset = key
    AR.State.enabled = true
    AR.State.features = AR.copyTable(preset.features)
    AR.State.strengths = AR.copyTable(preset.strengths)
    AR.Performance.setQuality(preset.quality, true)
    AR.Performance.setResolutionScale(preset.scale)
    if AR.Pipeline then
        AR.Pipeline.invalidateHistory("preset changed")
        AR.Pipeline.requestReconfigure("preset changed")
    end
    if AR.Materials and AR.Materials.started then
        AR.Materials.syncWorldMaterials()
        AR.Materials.syncVehicle()
    end
    AR.notify("Preset applied: " .. preset.label)
    return true
end

local function parseBoolean(value)
    value = string.lower(tostring(value or ""))
    return value == "on" or value == "1" or value == "true" or value == "yes" or value == "enable" or value == "enabled"
end

local function showStatus()
    local perf = AR.Performance.getStats()
    local pipe = AR.Pipeline.getStats()
    AR.notify(string.format("%s | %s | %.1f FPS / %.2f ms | post scale %.0f%% | depth %s | %d passes",
        AR.State.enabled and "ON" or "OFF", tostring(AR.State.quality), perf.fps or 0, perf.frameMs or 0,
        (pipe.actualScale or 0) * 100, perf.depthAvailable and "readable" or "not available", perf.activePasses or 0))
    AR.notify("Per-pass CPU submission is approximate; MTA does not expose GPU timestamp queries.", 170, 190, 202)
end

local function showHelp()
    AR.notify("Commands: /ars [menu|on|off|toggle|status|preset <name>|quality <tier>|scale <percent>|auto on/off|feature <name> on/off|debug <mode>]")
    AR.notify("Presets: ultra, high, cinematic, realistic, balanced, performance. Quality tiers: ultra, high, medium, low, compatibility.")
    AR.notify("Debug: /arsdebug <off|depth|motion|history|rejection|ssao|ssr|resolution>; /arsnextdebug cycles views.")
end

local function commandARS(_, action, value, extra)
    action = string.lower(tostring(action or "menu"))
    value = tostring(value or "")

    if action == "menu" or action == "ui" then
        AR.UI.toggle()
    elseif action == "on" or action == "enable" then
        AR.Pipeline.setEnabled(true)
        AR.notify("Rendering pipeline enabled.")
    elseif action == "off" or action == "disable" then
        AR.Pipeline.setEnabled(false)
        AR.notify("Rendering pipeline disabled; the native scene is left untouched.")
    elseif action == "toggle" then
        AR.Pipeline.setEnabled(not AR.State.enabled)
        AR.notify("Rendering pipeline " .. (AR.State.enabled and "enabled." or "disabled."))
    elseif action == "status" then
        showStatus()
    elseif action == "help" then
        showHelp()
    elseif action == "preset" then
        AR.applyPreset(value)
    elseif AR.Presets[normalizePreset(action)] then
        AR.applyPreset(action)
    elseif action == "quality" then
        if AR.Performance.setQuality(value) then
            AR.notify("Quality profile: " .. string.upper(value))
        else
            AR.notify("Valid profiles: ultra, high, medium, low, compatibility.", 255, 190, 120)
        end
    elseif action == "scale" then
        local requested = tonumber(value)
        if requested and requested > 1 then
            requested = requested / 100
        end
        if requested and AR.Performance.setResolutionScale(requested) then
            AR.notify(string.format("Post-process scale requested: %d%%.", math.floor(AR.State.resolutionScale * 100 + 0.5)))
        else
            AR.notify("Use /ars scale 100, 85, 75, 67 or 50.", 255, 190, 120)
        end
    elseif action == "auto" or action == "dynamic" then
        AR.State.dynamicResolution = parseBoolean(value)
        if not AR.State.dynamicResolution then
            AR.Performance.budgetLevel = 0
        end
        AR.notify("Dynamic resolution " .. (AR.State.dynamicResolution and "enabled." or "disabled."))
    elseif action == "feature" then
        local featureKey = string.lower(value)
        local feature = featureAliases[featureKey] or featureKey
        local stateValue = string.lower(tostring(extra or ""))
        local supported = AR.State.features[feature] ~= nil
        if supported and (stateValue == "on" or stateValue == "off" or stateValue == "1" or stateValue == "0") then
            local enabled = parseBoolean(stateValue)
            AR.Pipeline.setFeature(feature, enabled)
            AR.notify(feature .. " " .. (enabled and "enabled." or "disabled."))
        else
            AR.notify("Feature syntax: /ars feature <temporal|reconstruction|superResolution|taa|ssao|ssr|shadowEnhancement|vehicleResponse|materialEnhancement|sharpen|toneMapping|autoExposure|colorManagement> on|off", 255, 190, 120)
        end
    elseif action == "debug" then
        AR.Debug.setMode(value)
    else
        showHelp()
    end
end

function setARSRenderEnabled(enabled)
    return AR.Pipeline.setEnabled(enabled)
end

function getARSStatus()
    local pipelineStats = AR.Pipeline.getStats()
    return {
        enabled = AR.State.enabled,
        preset = AR.State.preset,
        quality = AR.State.quality,
        resolutionScale = pipelineStats.actualScale or AR.State.resolutionScale,
        depthAvailable = AR.State.depthAvailable == true,
        features = AR.copyTable(AR.State.features),
        performance = AR.Performance.getStats(),
        pipeline = pipelineStats
    }
end

local function startResource()
    if AR._started then
        return
    end
    AR._started = true

    AR.Performance.start()

    local desiredPreset = AR.Config.defaultPreset or "REALISTIC"
    if not AR.Presets[normalizePreset(desiredPreset)] then
        desiredPreset = "REALISTIC"
    end
    AR.applyPreset(desiredPreset)

    if (AR.Performance.device.pixelShaderVersion or 0) > 0 and AR.Performance.device.pixelShaderVersion < 2.0 then
        AR.Performance.setQuality("COMPATIBILITY")
        AR.log("Device reports less than pixel shader model 2.0. Compatibility quality is active; unsupported pixel passes are bypassed or use fixed-function copies.", 2)
    end

    AR.Materials.start()
    AR.Pipeline.start()
    AR.Debug.start()
    AR.UI.start()

    addCommandHandler(AR.Config.command, commandARS)
    AR.log("Resource started. Current client: " .. tostring(getVersion().sortable or "unknown") .. "; device: " .. tostring(AR.Performance.device.videoCardName or "unknown") .. "; depth: " .. (AR.State.depthAvailable and "available" or "unavailable") .. ".")
    AR.notify("Ready. Press F10 or use /ars for the control panel; /arsdebug depth shows the depth buffer.")
end

local function stopResource()
    if not AR._started then
        return
    end
    AR.UI.stop()
    AR.Debug.stop()
    AR.Pipeline.stop()
    AR.Materials.stop()
    AR.Performance.stop()
    AR._started = false
end

addEventHandler("onClientResourceStart", resourceRoot, startResource)
addEventHandler("onClientResourceStop", resourceRoot, stopResource)
