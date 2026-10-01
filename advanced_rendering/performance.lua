local AR = AdvancedRendering
AR.Performance = {
    averageFrameMs = 0,
    lastFrameTick = nil,
    frames = 0,
    fps = 0,
    device = {},
    budgetLevel = 0,
    overloadMs = 0,
    recoveryMs = 0,
    lastAdjustmentTick = 0,
    lastStatusTick = 0,
    passAverages = {},
    passSamples = {},
    cpuSubmitMs = 0
}

local function parseShaderVersion(value)
    if type(value) == "number" then
        return value
    end
    if type(value) == "string" then
        return tonumber(value:match("(%d+%.?%d*)"))
    end
    return nil
end

local function safeStatus()
    local ok, status = pcall(dxGetStatus)
    if ok and type(status) == "table" then
        return status
    end
    return {}
end

function AR.Performance.refreshDeviceInfo(force)
    local now = getTickCount()
    if not force and now - AR.Performance.lastStatusTick < 2000 then
        return AR.Performance.device
    end

    AR.Performance.lastStatusTick = now
    local status = safeStatus()
    local psVersion = parseShaderVersion(status.VideoCardPSVersion)
    local depthAvailable = status.UsingDepthBuffer == true
        and status.DepthBufferFormat ~= nil
        and string.lower(tostring(status.DepthBufferFormat)) ~= "unknown"

    AR.Performance.device = {
        videoCardName = tostring(status.VideoCardName or "unknown"),
        videoCardRAM = tonumber(status.VideoCardRAM) or 0,
        freeVideoMemory = tonumber(status.VideoMemoryFreeForMTA) or -1,
        pixelShaderVersion = psVersion or 0,
        maxRenderTargets = tonumber(status.VideoCardNumRenderTargets) or 0,
        depthAvailable = depthAvailable,
        rawStatus = status
    }
    AR.State.depthAvailable = depthAvailable

    if (psVersion or 0) < 2.0 then
        AR.log("Pixel shader model 2.0 is not reported by this device; shader passes will use their fixed-function fallback where possible.", 2)
    end
    if not depthAvailable then
        AR.log("Readable depth buffer is unavailable. Depth-dependent AO, SSR, depth rejection and depth debug are disabled; camera-only temporal motion remains available.", 2)
    end

    return AR.Performance.device
end

function AR.Performance.profileLimits()
    local quality = string.upper(tostring(AR.State.quality or "HIGH"))
    return AR.Config.qualityProfiles[quality] or AR.Config.qualityProfiles.HIGH
end

local function getScaleIndex(scale)
    local bestIndex, bestDelta = 1, math.huge
    for index, value in ipairs(AR.Config.scaleSteps) do
        local delta = math.abs(value - scale)
        if delta < bestDelta then
            bestIndex, bestDelta = index, delta
        end
    end
    return bestIndex
end

local function canAdjust()
    if not AR.State.dynamicResolution then
        return false
    end
    if AR.State.enabled == false then
        return false
    end
    if AR.UI and AR.UI.isOpen and AR.UI.isOpen() then
        return false
    end
    return true
end

local function setScaleFromIndex(index, reason)
    local steps = AR.Config.scaleSteps
    index = math.max(1, math.min(#steps, index))
    local scale = steps[index]
    local limits = AR.Performance.profileLimits()
    if scale < (limits.minScale or AR.Config.minScale) then
        scale = limits.minScale or AR.Config.minScale
        index = getScaleIndex(scale)
    end
    if math.abs(scale - (AR.State.resolutionScale or 1)) < 0.001 then
        return false
    end
    AR.State.resolutionScale = scale
    AR.Performance.lastAdjustmentTick = getTickCount()
    AR.Performance.overloadMs = 0
    AR.Performance.recoveryMs = 0
    AR.log(string.format("Dynamic resolution changed to %d%% (%s). This scales the post-process chain only; GTA's native scene is still rendered at display resolution.", math.floor(scale * 100 + 0.5), reason or "automatic"))
    if AR.Pipeline and AR.Pipeline.requestReconfigure then
        AR.Pipeline.requestReconfigure("resolution scale changed")
    end
    return true
end

function AR.Performance.setResolutionScale(scale, automatic)
    scale = tonumber(scale)
    if not scale then
        return false
    end
    local nearest = AR.Config.scaleSteps[getScaleIndex(scale)]
    AR.State.resolutionScale = nearest
    if automatic ~= nil then
        AR.State.dynamicResolution = automatic == true
    end
    AR.Performance.overloadMs = 0
    AR.Performance.recoveryMs = 0
    if AR.Pipeline and AR.Pipeline.requestReconfigure then
        AR.Pipeline.requestReconfigure("manual resolution scale change")
    end
    return true
end

function AR.Performance.setQuality(name, preserveFeatureChoices)
    name = string.upper(tostring(name or ""))
    local profile = AR.Config.qualityProfiles[name]
    if not profile then
        return false
    end
    AR.State.quality = name
    AR.State.resolutionScale = profile.baseScale or 0.75
    if not preserveFeatureChoices then
        AR.State.features.temporal = profile.temporal == true
        AR.State.features.taa = profile.taa == true
        AR.State.features.ssao = profile.ssao == true
        AR.State.features.ssr = profile.ssr == true
        AR.State.features.shadowEnhancement = profile.shadow == true
        AR.State.features.materialEnhancement = profile.material == true
        AR.State.features.vehicleResponse = profile.vehicle == true
        if profile.reconstruction ~= nil then AR.State.features.reconstruction = profile.reconstruction == true end
        if profile.superResolution ~= nil then AR.State.features.superResolution = profile.superResolution == true end
        if profile.sharpen ~= nil then AR.State.features.sharpen = profile.sharpen == true end
        if AR.Materials and AR.Materials.started then
            AR.Materials.syncWorldMaterials()
            AR.Materials.syncVehicle()
        end
        if AR.Pipeline and AR.Pipeline.invalidateHistory then
            AR.Pipeline.invalidateHistory("quality profile changed")
        end
    end
    AR.Performance.budgetLevel = 0
    AR.Performance.overloadMs = 0
    AR.Performance.recoveryMs = 0
    if AR.Pipeline and AR.Pipeline.requestReconfigure then
        AR.Pipeline.requestReconfigure("quality profile changed")
    end
    return true
end

function AR.Performance.getFeatureAllowed(feature)
    local budget = AR.Performance.budgetLevel or 0
    if budget >= 1 and (feature == "ssr" or feature == "shadowEnhancement") then
        return false
    end
    if budget >= 2 and feature == "ssao" then
        return false
    end
    if budget >= 3 and (feature == "materialEnhancement" or feature == "vehicleResponse") then
        return false
    end
    return true
end

function AR.Performance.recordPass(name, milliseconds)
    local value = math.max(0, tonumber(milliseconds) or 0)
    local old = AR.Performance.passAverages[name] or value
    AR.Performance.passAverages[name] = old * 0.82 + value * 0.18
    AR.Performance.passSamples[name] = (AR.Performance.passSamples[name] or 0) + 1
end

function AR.Performance.setPipelineSubmitTime(milliseconds, activePasses)
    AR.Performance.cpuSubmitMs = tonumber(milliseconds) or 0
    AR.Performance.activePasses = activePasses or 0
end

function AR.Performance.sampleFrame()
    local now = getTickCount()
    local perf = AR.Performance
    if perf.lastFrameTick then
        local delta = now - perf.lastFrameTick
        if delta < 0 then
            delta = delta + 4294967296
        end
        if delta > 0 and delta < 1000 then
            if perf.averageFrameMs <= 0 then
                perf.averageFrameMs = delta
            else
                perf.averageFrameMs = perf.averageFrameMs * 0.90 + delta * 0.10
            end
            perf.fps = 1000 / math.max(perf.averageFrameMs, 0.1)
            perf.frames = perf.frames + 1
            AR.Performance.refreshDeviceInfo(false)
            AR.Performance.updateAdaptiveQuality(delta, now)
        end
    end
    perf.lastFrameTick = now
end

function AR.Performance.updateAdaptiveQuality(delta, now)
    local perf = AR.Performance
    if not canAdjust() then
        perf.overloadMs = 0
        perf.recoveryMs = 0
        return
    end

    if now - perf.lastAdjustmentTick < AR.Config.adaptiveCooldownMs then
        return
    end

    local frameMs = perf.averageFrameMs
    if frameMs > AR.Config.adaptiveDownThresholdMs then
        perf.overloadMs = perf.overloadMs + delta
        perf.recoveryMs = 0
    elseif frameMs < AR.Config.adaptiveUpThresholdMs then
        perf.recoveryMs = perf.recoveryMs + delta
        perf.overloadMs = 0
    else
        perf.overloadMs = math.max(0, perf.overloadMs - delta * 0.5)
        perf.recoveryMs = math.max(0, perf.recoveryMs - delta * 0.5)
    end

    if perf.overloadMs >= AR.Config.adaptiveDownHoldMs then
        local idx = getScaleIndex(AR.State.resolutionScale or 1)
        local lowerIdx = math.min(#AR.Config.scaleSteps, idx + 1)
        local minScale = perf.profileLimits().minScale or AR.Config.minScale
        if AR.Config.scaleSteps[lowerIdx] >= minScale and lowerIdx ~= idx then
            setScaleFromIndex(lowerIdx, "sustained frame-time pressure")
        elseif perf.budgetLevel < 3 then
            perf.budgetLevel = perf.budgetLevel + 1
            perf.lastAdjustmentTick = now
            perf.overloadMs = 0
            AR.log("Adaptive performance reduced optional passes (budget level " .. perf.budgetLevel .. "). Temporal accumulation is retained when possible.")
        else
            perf.overloadMs = 0
        end
    elseif perf.recoveryMs >= AR.Config.adaptiveUpHoldMs then
        if perf.budgetLevel > 0 then
            perf.budgetLevel = perf.budgetLevel - 1
            perf.lastAdjustmentTick = now
            perf.recoveryMs = 0
            AR.log("Adaptive performance restored one optional-pass budget level.")
        else
            local idx = getScaleIndex(AR.State.resolutionScale or 1)
            local higherIdx = math.max(1, idx - 1)
            if higherIdx ~= idx then
                setScaleFromIndex(higherIdx, "sustained frame-time headroom")
            else
                perf.recoveryMs = 0
            end
        end
    end
end

function AR.Performance.getStats()
    local device = AR.Performance.device or {}
    return {
        fps = AR.Performance.fps or 0,
        frameMs = AR.Performance.averageFrameMs or 0,
        cpuSubmitMs = AR.Performance.cpuSubmitMs or 0,
        activePasses = AR.Performance.activePasses or 0,
        budgetLevel = AR.Performance.budgetLevel or 0,
        freeVideoMemory = device.freeVideoMemory or -1,
        videoCardName = device.videoCardName or "unknown",
        pixelShaderVersion = device.pixelShaderVersion or 0,
        depthAvailable = device.depthAvailable == true,
        passAverages = AR.Performance.passAverages or {}
    }
end

function AR.Performance.start()
    AR.Performance.refreshDeviceInfo(true)
    AR.Performance.lastFrameTick = getTickCount()
    addEventHandler("onClientPreRender", root, AR.Performance.sampleFrame)
end

function AR.Performance.stop()
    removeEventHandler("onClientPreRender", root, AR.Performance.sampleFrame)
end
