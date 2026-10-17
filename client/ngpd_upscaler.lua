--[[
  NextGenPoliceDepartment - 4K Spatial Upscaling System (AMD FSR 1.0 EASU + RCAS)
  Target Hardware: AMD Radeon RX 580 2048SP | Ryzen 5 3600X | 16 GB RAM | DirectX 9

  Architecture (Two-Pass Spatial Reconstruction + Native-Res HUD):
    Pass 1 (shaders/upscale_easu.fx):
      Captures the scene at internal scale (50%..100% of target/4K output) via dxCreateScreenSource
      and runs 12-tap anisotropic Edge-Adaptive Spatial Upsampling (EASU) + optional screen-space
      Golden-Hour solar Mie bloom into an intermediate render target.
    Pass 2 (shaders/upscale_rcas.fx):
      Applies 5-tap ringing-free Robust Contrast-Adaptive Sharpening (RCAS) at output resolution,
      preserving aspect ratio (pillarbox/letterbox if needed), followed by crisp native-resolution
      HUD/UI telemetry overlay.
    Device-Reset & Fallback Safety:
      Listens to onClientRestore (DirectX 9 device reset / Alt-Tab) to rebuild render targets cleanly,
      and falls back to native rendering if VRAM is insufficient.
]]

NGPD.upscaler = {
    enabled = false,
    preset = "quality",
    scale = 0.67,
    sharpness = 0.72,
    edgeSharpness = 1.00,
    preserveAspect = true,
    showBadge = true,
    atmosBloom = 0.35,
    screenSrc = nil,
    interRT = nil,
    easuShader = nil,
    rcasShader = nil,
    easuTech = nil,
    rcasTech = nil,
    internalW = 0,
    internalH = 0,
    outW = 0,
    outH = 0,
    vpX = 0,
    vpY = 0,
    vpW = 0,
    vpH = 0,
    fallbackReason = nil,
}
local U = NGPD.upscaler

local function releaseResources()
    if U.easuShader and isElement(U.easuShader) then destroyElement(U.easuShader) end
    if U.rcasShader and isElement(U.rcasShader) then destroyElement(U.rcasShader) end
    if U.interRT and isElement(U.interRT) then destroyElement(U.interRT) end
    if U.screenSrc and isElement(U.screenSrc) then destroyElement(U.screenSrc) end
    U.easuShader, U.rcasShader, U.interRT, U.screenSrc = nil, nil, nil, nil
end

local function computeDimensions()
    local sw, sh = 1920, 1080
    if guiGetScreenSize then
        local w, h = guiGetScreenSize()
        if w and h and w >= 64 and h >= 64 then sw, sh = w, h end
    end
    U.outW, U.outH = sw, sh
    local s = NGPD.clamp(U.scale or 0.67, 0.50, 1.00)
    U.internalW = math.max(64, math.floor((sw * s) / 2 + 0.5) * 2)
    U.internalH = math.max(64, math.floor((sh * s) / 2 + 0.5) * 2)

    U.vpX, U.vpY, U.vpW, U.vpH = 0, 0, sw, sh
    if U.preserveAspect then
        local targetAspect = 16.0 / 9.0
        local actualAspect = sw / math.max(1, sh)
        if math.abs(actualAspect - targetAspect) > 0.02 then
            if actualAspect > targetAspect then
                U.vpW = math.floor(sh * targetAspect + 0.5)
                U.vpX = math.floor((sw - U.vpW) / 2)
            else
                U.vpH = math.floor(sw / targetAspect + 0.5)
                U.vpY = math.floor((sh - U.vpH) / 2)
            end
        end
    end
end

function U.rebuildPipeline()
    releaseResources()
    U.fallbackReason = nil
    if not U.enabled then return true end

    computeDimensions()
    if not dxCreateScreenSource or not dxCreateRenderTarget or not dxCreateShader then
        U.fallbackReason = "DX9 render-target API unavailable"
        U.enabled = false
        return false
    end

    U.screenSrc = dxCreateScreenSource(U.internalW, U.internalH)
    if not U.screenSrc then
        U.fallbackReason = "dxCreateScreenSource failed (VRAM limit)"
        U.enabled = false
        releaseResources()
        outputChatBox("[NGPD Upscaler] Could not allocate internal screen source - falling back to native rendering.", 255, 200, 80)
        return false
    end

    U.interRT = dxCreateRenderTarget(U.outW, U.outH, false)
    if not U.interRT then
        U.fallbackReason = "dxCreateRenderTarget failed (VRAM limit)"
        U.enabled = false
        releaseResources()
        outputChatBox("[NGPD Upscaler] Could not allocate EASU render target - falling back to native rendering.", 255, 200, 80)
        return false
    end

    local easu, eTech = dxCreateShader("shaders/upscale_easu.fx", 0, 0, false, "other")
    local rcas, rTech = dxCreateShader("shaders/upscale_rcas.fx", 0, 0, false, "other")
    if not easu or not rcas or eTech == "fallback" or rTech == "fallback" then
        if easu and isElement(easu) then destroyElement(easu) end
        if rcas and isElement(rcas) then destroyElement(rcas) end
        U.fallbackReason = "EASU/RCAS shader compilation fell back"
        U.enabled = false
        releaseResources()
        outputChatBox("[NGPD Upscaler] GPU did not validate EASU/RCAS shaders - falling back to native rendering.", 255, 200, 80)
        return false
    end

    U.easuShader, U.easuTech = easu, eTech
    U.rcasShader, U.rcasTech = rcas, rTech

    dxSetShaderValue(U.easuShader, "gInputTex", U.screenSrc)
    dxSetShaderValue(U.easuShader, "gInputSize", U.internalW, U.internalH)
    dxSetShaderValue(U.easuShader, "gInputInv", 1.0 / U.internalW, 1.0 / U.internalH)
    dxSetShaderValue(U.easuShader, "gOutputSize", U.outW, U.outH)
    dxSetShaderValue(U.easuShader, "gEdgeSharpness", U.edgeSharpness)
    dxSetShaderValue(U.easuShader, "gAtmosBloom", U.atmosBloom)

    dxSetShaderValue(U.rcasShader, "gUpscaledTex", U.interRT)
    dxSetShaderValue(U.rcasShader, "gTexelSize", 1.0 / U.outW, 1.0 / U.outH)
    dxSetShaderValue(U.rcasShader, "gSharpness", U.sharpness)
    return true
end

local function renderUpscalerFrame()
    if not U.enabled or not U.screenSrc or not U.interRT or not U.easuShader or not U.rcasShader then
        return
    end
    -- Detect dynamic display resolution changes
    if guiGetScreenSize then
        local sw, sh = guiGetScreenSize()
        if sw and sh and (sw ~= U.outW or sh ~= U.outH) then
            U.rebuildPipeline()
            if not U.enabled then return end
        end
    end

    -- Capture scene at internal resolution
    dxUpdateScreenSource(U.screenSrc, true)

    -- Update screen-space sun position for golden-hour atmospheric glare in Pass 1
    if NGPD.lighting and NGPD.lighting.getSunScreenPos then
        local su, sv, sw = NGPD.lighting.getSunScreenPos()
        dxSetShaderValue(U.easuShader, "gSunScreenPos", su, sv, sw)
        local sc = (NGPD.shaders and NGPD.shaders.env and NGPD.shaders.env.gSunColor) or { 1.0, 0.78, 0.48 }
        dxSetShaderValue(U.easuShader, "gSunAtmosColor", sc[1], sc[2], sc[3])
    end

    -- Pass 1: EASU 12-tap anisotropic spatial upsampling into intermediate RT
    dxSetRenderTarget(U.interRT, true)
    dxDrawImage(0, 0, U.outW, U.outH, U.easuShader)
    dxSetRenderTarget()

    -- Letterbox / pillarbox bars if aspect ratio preservation is active on non-16:9 displays
    if U.preserveAspect and (U.vpX > 0 or U.vpY > 0) and dxDrawRectangle then
        dxDrawRectangle(0, 0, U.outW, U.outH, tocolor(0, 0, 0, 255))
    end

    -- Pass 2: RCAS 5-tap contrast-adaptive sharpening to output display viewport
    dxDrawImage(U.vpX, U.vpY, U.vpW, U.vpH, U.rcasShader)

    -- Native-resolution HUD status badge (rendered AFTER upscaling so UI text is razor-sharp)
    if U.showBadge and dxDrawText and dxDrawRectangle then
        local pct = math.floor(U.scale * 100 + 0.5)
        local savings = math.floor((1.0 - (U.internalW * U.internalH) / math.max(1, U.outW * U.outH)) * 100 + 0.5)
        local label = string.format("NGPD 4K FSR-EASU+RCAS [%s] %dx%d -> %dx%d (%d%% Scale | -%d%% Pixels | Sharp %d%%)",
            tostring(U.preset):upper(), U.internalW, U.internalH, U.outW, U.outH, pct, savings, math.floor(U.sharpness * 100 + 0.5))
        dxDrawRectangle(U.outW - 560, 14, 544, 26, tocolor(12, 16, 24, 185))
        dxDrawText(label, U.outW - 550, 18, U.outW - 22, 36, tocolor(255, 208, 128, 235), 1.0, "default-bold", "right", "center")
    end
end

function U.enable(presetName)
    local cfg = NGPD_CONFIG.upscaler or {}
    local presets = cfg.presets or {}
    if presetName and presets[presetName] then
        U.preset = presetName
        U.scale = presets[presetName].scale
        U.sharpness = presets[presetName].sharpness
    end
    U.enabled = true
    if U.rebuildPipeline() then
        removeEventHandler("onClientHUDRender", root, renderUpscalerFrame)
        addEventHandler("onClientHUDRender", root, renderUpscalerFrame, true, "high+10")
        return true
    end
    return false
end

function U.disable()
    U.enabled = false
    removeEventHandler("onClientHUDRender", root, renderUpscalerFrame)
    releaseResources()
end

function U.applyFromProfile(profile)
    if not profile then return end
    if profile.upscalerEnabled then
        U.scale = profile.upscalerScale or 0.67
        U.sharpness = profile.upscalerSharpness or 0.72
        U.enable(profile.upscalerPreset or "quality")
    elseif U.enabled then
        U.disable()
    end
end

-- DirectX 9 device reset recovery (Alt-Tab / fullscreen toggle)
addEventHandler("onClientRestore", root, function(didClearRenderTargets)
    if U.enabled and didClearRenderTargets then
        U.rebuildPipeline()
    end
end)

addCommandHandler("ngpd_upscale", function(_, arg)
    arg = arg and arg:lower() or ""
    local presets = (NGPD_CONFIG.upscaler and NGPD_CONFIG.upscaler.presets) or {}
    if arg == "on" or arg == "enable" then
        if U.enable(U.preset) then
            outputChatBox(string.format("[NGPD Upscaler] Enabled (%s: %dx%d -> %dx%d, RCAS %.0f%%)",
                U.preset:upper(), U.internalW, U.internalH, U.outW, U.outH, U.sharpness * 100), 150, 200, 255)
        end
    elseif arg == "off" or arg == "disable" then
        U.disable()
        outputChatBox("[NGPD Upscaler] Disabled (Native resolution).", 150, 200, 255)
    elseif arg == "hud" or arg == "badge" then
        U.showBadge = not U.showBadge
        outputChatBox("[NGPD Upscaler] Native-res HUD telemetry badge: " .. (U.showBadge and "ON" or "OFF"), 150, 200, 255)
    elseif arg == "aspect" then
        U.preserveAspect = not U.preserveAspect
        if U.enabled then U.rebuildPipeline() end
        outputChatBox("[NGPD Upscaler] 16:9 aspect-ratio preservation: " .. (U.preserveAspect and "ON" or "OFF"), 150, 200, 255)
    elseif presets[arg] then
        if U.enable(arg) then
            outputChatBox(string.format("[NGPD Upscaler] Preset '%s' active (%dx%d -> %dx%d, RCAS %.0f%%)",
                presets[arg].label, U.internalW, U.internalH, U.outW, U.outH, U.sharpness * 100), 150, 200, 255)
        end
    else
        outputChatBox(string.format("[NGPD Upscaler] %s | Preset: %s | Scale: %d%% | Sharpness: %d%%",
            U.enabled and "ON" or "OFF", tostring(U.preset), math.floor(U.scale * 100 + 0.5), math.floor(U.sharpness * 100 + 0.5)), 150, 200, 255)
        outputChatBox("[NGPD Upscaler] Usage: /ngpd_upscale <on|off|performance|balanced|quality|ultra_quality|native|hud|aspect>", 150, 200, 255)
    end
end)

addCommandHandler("ngpd_scale", function(_, val)
    local pct = tonumber(val)
    if not pct or pct < 50 or pct > 100 then
        return outputChatBox("[NGPD Upscaler] Usage: /ngpd_scale <50..100> (internal resolution percentage)", 150, 200, 255)
    end
    U.scale = pct / 100.0
    U.preset = "custom"
    if U.enabled then U.rebuildPipeline() else U.enable() end
    outputChatBox(string.format("[NGPD Upscaler] Internal scale set to %d%% (%dx%d -> %dx%d)",
        pct, U.internalW, U.internalH, U.outW, U.outH), 150, 200, 255)
end)

addCommandHandler("ngpd_sharpen", function(_, val)
    local pct = tonumber(val)
    if not pct or pct < 0 or pct > 100 then
        return outputChatBox("[NGPD Upscaler] Usage: /ngpd_sharpen <0..100> (RCAS contrast-adaptive sharpening)", 150, 200, 255)
    end
    U.sharpness = pct / 100.0
    if U.rcasShader and isElement(U.rcasShader) then
        dxSetShaderValue(U.rcasShader, "gSharpness", U.sharpness)
    end
    outputChatBox(string.format("[NGPD Upscaler] RCAS sharpening set to %d%%", pct), 150, 200, 255)
end)

addEventHandler("onClientResourceStop", resourceRoot, function()
    U.disable()
end)
