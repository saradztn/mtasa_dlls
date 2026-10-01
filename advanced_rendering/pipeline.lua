local AR = AdvancedRendering
AR.Pipeline = {
    shaders = {},
    shaderUsable = {},
    shaderTechnique = {},
    pool = nil,
    screenSource = nil,
    screenSourceWidth = 0,
    screenSourceHeight = 0,
    screenWidth = 0,
    screenHeight = 0,
    internalWidth = 0,
    internalHeight = 0,
    actualScale = 1,
    historyIndex = 0,
    historyValid = false,
    exposureIndex = 0,
    exposureValid = false,
    previousCamera = nil,
    previousJitter = { 0, 0 },
    frameIndex = 0,
    depthReady = false,
    started = false,
    reconfigureReason = nil,
    lastCaptureWarning = false,
    lastTargetWarning = false,
    lastScreenSourceWarningTick = nil,
    allocationFailureLogged = false,
    lastAllocationLogTick = nil,
    lastPoolFailureLogTick = nil,
    lastPassNames = {},
    blueNoise = nil,
    samplingNoise = nil,
    retryAfterTick = 0
}

local P = AR.Pipeline
local shaderPaths = {
    core = "shaders/core.fx",
    depth = "shaders/depth.fx",
    motion = "shaders/motion_vectors.fx",
    temporal = "shaders/temporal.fx",
    taa = "shaders/taa.fx",
    reconstruction = "shaders/reconstruction.fx",
    superResolution = "shaders/super_resolution.fx",
    ssao = "shaders/ssao.fx",
    ssr = "shaders/ssr.fx",
    shadow = "shaders/shadow_enhance.fx",
    sharpen = "shaders/sharpen.fx",
    luminance = "shaders/luminance.fx",
    tonemap = "shaders/tonemap.fx",
    finalComposite = "shaders/final_composite.fx",
    debug = "shaders/debug.fx"
}

local function isValidElement(element)
    return element ~= nil and isElement(element)
end

local function getNoiseScale()
    local size = math.max(1, tonumber(AR.Config.blueNoiseSize) or 64)
    return { P.internalWidth / size, P.internalHeight / size }
end

local function safeDestroy(element)
    if isValidElement(element) then
        destroyElement(element)
    end
end

local function lowerString(value)
    return string.lower(tostring(value or ""))
end

local function isFallbackTechnique(name)
    local value = lowerString(name)
    return value:find("fallback", 1, true) ~= nil or value:find("nodepth", 1, true) ~= nil
end

local function makeShader(name, path)
    local shader, technique = dxCreateShader(path)
    if not isValidElement(shader) then
        AR.log("Failed to compile effect '" .. name .. "' from " .. path .. ". The remaining pipeline will bypass this pass; inspect debugscript 3 for the Direct3D compiler diagnostic.", 1)
        P.shaderUsable[name] = false
        P.shaderTechnique[name] = nil
        return nil
    end

    local techniqueName = tostring(technique or "unknown")
    P.shaders[name] = shader
    P.shaderTechnique[name] = techniqueName
    P.shaderUsable[name] = not isFallbackTechnique(techniqueName)
    local qualityNote = ""
    if lowerString(techniqueName):find("compatibility", 1, true) then
        qualityNote = " (PS 2.0 compatibility kernel; reduced reconstruction quality)"
    elseif not P.shaderUsable[name] then
        qualityNote = " (copy/compatibility technique)"
    end
    AR.log("Effect '" .. name .. "' loaded with technique '" .. techniqueName .. "'." .. qualityNote)
    return shader, techniqueName
end

local function createShaders()
    for name, path in pairs(shaderPaths) do
        if name ~= "depth" then
            makeShader(name, path)
        end
    end

    local depthTechnique
    if AR.State.depthAvailable then
        local _, chosen = makeShader("depth", shaderPaths.depth)
        depthTechnique = chosen
        P.depthReady = isValidElement(P.shaders.depth) and P.shaderUsable.depth
    else
        P.depthReady = false
    end
    if not P.depthReady then
        AR.log("Depth extraction is not active (native depth unavailable or the depth technique did not validate).", 2)
    elseif depthTechnique then
        AR.log("Readable depth extraction enabled using technique '" .. tostring(depthTechnique) .. "'.")
    end

    local noise = dxCreateTexture("textures/blue_noise.png")
    if isValidElement(noise) then
        P.blueNoise = noise
    else
        AR.log("Blue-noise texture failed to load; SSAO will use the screen source as a low-quality sampling pattern.", 2)
    end
    local samplingNoise = dxCreateTexture("textures/sampling_noise.png")
    if isValidElement(samplingNoise) then
        P.samplingNoise = samplingNoise
    else
        AR.log("Sampling-noise texture failed to load; SSR will use the blue-noise tile if it is available.", 2)
    end
end

local function destroyPool(pool)
    if not pool then
        return
    end
    for _, element in pairs(pool) do
        safeDestroy(element)
    end
end

local function createTarget(pool, name, width, height)
    local target = dxCreateRenderTarget(width, height, false)
    if not isValidElement(target) then
        if not P.allocationFailureLogged then
            local now = getTickCount()
            if not P.lastAllocationLogTick or now - P.lastAllocationLogTick >= 15000 then
                AR.log(string.format("Render target allocation failed: %s (%dx%d, x8r8g8b8). Trying lower post-process scales; retries are throttled.", name, width, height), 2)
                P.lastAllocationLogTick = now
            end
            P.allocationFailureLogged = true
        end
        return false
    end
    pool[name] = target
    return true
end

local function buildPool(scale)
    local width = math.max(2, math.floor(P.screenWidth * scale + 0.5))
    local height = math.max(2, math.floor(P.screenHeight * scale + 0.5))
    local newPool = {}
    local internalTargets = {
        "workA", "workB", "history0", "history1", "depth0", "depth1",
        "motion", "ssaoResult", "ssrResult"
    }

    for _, name in ipairs(internalTargets) do
        if not createTarget(newPool, name, width, height) then
            destroyPool(newPool)
            return nil
        end
    end
    if not createTarget(newPool, "output", P.screenWidth, P.screenHeight) then
        destroyPool(newPool)
        return nil
    end
    if not createTarget(newPool, "exposure0", 1, 1) then
        destroyPool(newPool)
        return nil
    end
    if not createTarget(newPool, "exposure1", 1, 1) then
        destroyPool(newPool)
        return nil
    end

    return newPool, width, height
end

local function getScaleIndex(scale)
    local best, distance = 1, math.huge
    for index, candidate in ipairs(AR.Config.scaleSteps) do
        local current = math.abs(candidate - scale)
        if current < distance then
            best, distance = index, current
        end
    end
    return best
end

local function destroyScreenSource()
    safeDestroy(P.screenSource)
    P.screenSource = nil
    P.screenSourceWidth = 0
    P.screenSourceHeight = 0
end

local function ensureScreenSource(width, height)
    if isValidElement(P.screenSource) and width == P.screenSourceWidth and height == P.screenSourceHeight then
        return true
    end
    destroyScreenSource()
    local source = dxCreateScreenSource(width, height)
    if not isValidElement(source) then
        local now = getTickCount()
        if not P.lastScreenSourceWarningTick or now - P.lastScreenSourceWarningTick >= 15000 then
            AR.log(string.format("Could not create the %dx%d scene screen source. No post-process output will be drawn until it can be allocated; retries are throttled.", width, height), 1)
            P.lastScreenSourceWarningTick = now
        end
        return false
    end
    P.lastScreenSourceWarningTick = nil
    P.screenSource = source
    P.screenSourceWidth = width
    P.screenSourceHeight = height
    return true
end

local function reconfigurePool(reason)
    local width, height = guiGetScreenSize()
    width, height = math.max(2, math.floor(width)), math.max(2, math.floor(height))
    if width < 2 or height < 2 then
        return false
    end

    local dimensionsChanged = width ~= P.screenWidth or height ~= P.screenHeight
    P.screenWidth, P.screenHeight = width, height
    -- Free the old RT pool before requesting a resized full-screen source; this
    -- avoids deadlocking recovery when the old pool consumed the remaining VRAM.
    destroyPool(P.pool)
    P.pool = nil
    P.ready = false
    if not ensureScreenSource(width, height) then
        P.retryAfterTick = getTickCount() + 3000
        return false
    end

    P.allocationFailureLogged = false

    local requestedScale = math.max(AR.Config.minScale, math.min(AR.Config.maxScale, tonumber(AR.State.resolutionScale) or 0.75))
    local startIndex = getScaleIndex(requestedScale)
    local selectedPool, selectedWidth, selectedHeight, selectedScale
    for index = startIndex, #AR.Config.scaleSteps do
        local attemptScale = AR.Config.scaleSteps[index]
        if attemptScale <= requestedScale + 0.001 then
            local candidate, targetWidth, targetHeight = buildPool(attemptScale)
            if candidate then
                selectedPool, selectedWidth, selectedHeight, selectedScale = candidate, targetWidth, targetHeight, attemptScale
                break
            end
        end
    end

    if not selectedPool then
        local now = getTickCount()
        if not P.lastPoolFailureLogTick or now - P.lastPoolFailureLogTick >= 15000 then
            AR.log("The persistent render-target pool could not be allocated at the minimum supported scale. The resource will leave the game image untouched, keep the control panel available and retry later.", 1)
            P.lastPoolFailureLogTick = now
        end
        P.internalWidth, P.internalHeight = 0, 0
        P.retryAfterTick = now + 3000
        return false
    end

    P.pool = selectedPool
    P.internalWidth, P.internalHeight = selectedWidth, selectedHeight
    P.actualScale = selectedScale
    P.retryAfterTick = 0
    P.lastPoolFailureLogTick = nil
    P.ready = true
    P.historyIndex = 0
    P.historyValid = false
    P.exposureIndex = 0
    P.exposureValid = false
    P.previousCamera = nil
    P.previousJitter = { 0, 0 }
    P.frameIndex = 0

    if math.abs(AR.State.resolutionScale - selectedScale) > 0.001 then
        AR.State.resolutionScale = selectedScale
        AR.log(string.format("Render-target allocation fallback selected %d%% internal post-process resolution.", math.floor(selectedScale * 100 + 0.5)), 2)
    end

    AR.log(string.format("Render-target pool ready (%s): display %dx%d, post-process %dx%d (%d%%). Targets are persistent and reused; none are allocated per frame.", reason or "reconfigure", width, height, selectedWidth, selectedHeight, math.floor(selectedScale * 100 + 0.5)))
    if dimensionsChanged then
        P.historyValid = false
    end
    return true
end

function P.requestReconfigure(reason)
    P.reconfigureReason = tostring(reason or "requested")
end

function P.invalidateHistory(reason)
    if P.historyValid then
        AR.log("Temporal history reset" .. (reason and (": " .. tostring(reason)) or "."))
    end
    P.historyValid = false
    P.exposureValid = false
    P.previousCamera = nil
    P.previousJitter = { 0, 0 }
end

local function setValue(shader, name, value)
    if not isValidElement(shader) then
        return false
    end
    if type(value) == "table" then
        return dxSetShaderValue(shader, name, unpack(value))
    end
    return dxSetShaderValue(shader, name, value)
end

local function drawToTarget(passName, target, shader, width, height, values)
    if not isValidElement(target) or not isValidElement(shader) then
        return false
    end
    if values then
        for name, value in pairs(values) do
            if value ~= nil then
                setValue(shader, name, value)
            end
        end
    end

    local start = getTickCount()
    local selected = dxSetRenderTarget(target, true)
    if not selected then
        dxSetRenderTarget()
        dxSetBlendMode("blend")
        if not P.lastTargetWarning then
            AR.log("Could not bind render target for pass '" .. passName .. "'. The current output frame is skipped to avoid sampling an invalid target.", 1)
            P.lastTargetWarning = true
        end
        return false
    end
    P.lastTargetWarning = false

    dxSetBlendMode("overwrite")
    local drawn = dxDrawImage(0, 0, width, height, shader)
    dxSetBlendMode("blend")
    dxSetRenderTarget()

    local elapsed = getTickCount() - start
    if AR.Performance then
        AR.Performance.recordPass(passName, elapsed)
    end
    return drawn ~= false
end

local function drawFullscreenToScreen(shader, width, height)
    if not isValidElement(shader) then
        return false
    end
    dxSetRenderTarget()
    dxSetBlendMode("blend")
    local start = getTickCount()
    local drawn = dxDrawImage(0, 0, width, height, shader)
    if AR.Performance then
        AR.Performance.recordPass("screen_output", getTickCount() - start)
    end
    return drawn ~= false
end

local function runPass(passName, targetName, width, height, values)
    if not P.shaderUsable[passName] and passName ~= "core" and passName ~= "superResolution" and passName ~= "finalComposite" then
        return false
    end
    local shader = P.shaders[passName]
    local target = P.pool and P.pool[targetName]
    if not isValidElement(shader) or not isValidElement(target) then
        return false
    end
    return drawToTarget(passName, target, shader, width, height, values)
end

local function normalize3(x, y, z)
    local length = math.sqrt(x * x + y * y + z * z)
    if length < 0.00001 then
        return 0, 1, 0
    end
    return x / length, y / length, z / length
end

local function dot3(ax, ay, az, bx, by, bz)
    return ax * bx + ay * by + az * bz
end

local function cross3(ax, ay, az, bx, by, bz)
    return ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
end

local function clamp(value, low, high)
    return math.max(low, math.min(high, value))
end

local function readCamera()
    local cx, cy, cz, lx, ly, lz, roll, fov = getCameraMatrix()
    if type(cx) ~= "number" or type(cy) ~= "number" or type(cz) ~= "number"
        or type(lx) ~= "number" or type(ly) ~= "number" or type(lz) ~= "number" then
        return nil
    end

    local fx, fy, fz = normalize3(lx - cx, ly - cy, lz - cz)
    local rx, ry, rz = cross3(fx, fy, fz, 0, 0, 1)
    rx, ry, rz = normalize3(rx, ry, rz)
    local ux, uy, uz = cross3(rx, ry, rz, fx, fy, fz)
    ux, uy, uz = normalize3(ux, uy, uz)

    fov = tonumber(fov) or 70
    if fov > math.pi then
        fov = math.rad(fov)
    end
    fov = clamp(fov, math.rad(25), math.rad(120))
    local aspect = P.screenWidth / math.max(P.screenHeight, 1)
    local focalX = 0.5 / math.tan(fov * 0.5)
    local focalY = focalX * aspect

    return {
        x = cx, y = cy, z = cz,
        fx = fx, fy = fy, fz = fz,
        rx = rx, ry = ry, rz = rz,
        ux = ux, uy = uy, uz = uz,
        fov = fov, focalX = focalX, focalY = focalY
    }
end

local function halton(index, base)
    local fraction, result = 1, 0
    while index > 0 do
        fraction = fraction / base
        result = result + fraction * (index % base)
        index = math.floor(index / base)
    end
    return result
end

local function getFrameJitter()
    if not AR.State.features.temporal or P.actualScale >= 0.999 then
        return { 0, 0 }
    end
    local sample = (P.frameIndex % 8) + 1
    return { halton(sample, 2) - 0.5, halton(sample, 3) - 0.5 }
end

local function updateCameraMotion(currentCamera, jitter)
    local motion = { 0, 0, 0, 0 }
    local forwardMotion = 0
    local currentJitterDelta = { 0, 0 }
    local historyValid = P.historyValid
    local previous = P.previousCamera
    if historyValid and not currentCamera then
        P.invalidateHistory("camera matrix unavailable")
        historyValid = false
    end

    if previous and currentCamera and historyValid then
        local dx = currentCamera.x - previous.x
        local dy = currentCamera.y - previous.y
        local dz = currentCamera.z - previous.z
        local positionDelta = math.sqrt(dx * dx + dy * dy + dz * dz)
        local directionDot = clamp(dot3(currentCamera.fx, currentCamera.fy, currentCamera.fz, previous.fx, previous.fy, previous.fz), -1, 1)
        local angularDelta = math.acos(directionDot)
        local fovDelta = math.abs(currentCamera.fov - previous.fov)

        if positionDelta > 30 or angularDelta > 0.70 or fovDelta > math.rad(12) then
            P.invalidateHistory("camera cut or large camera discontinuity")
            historyValid = false
        else
            local dfx = currentCamera.fx - previous.fx
            local dfy = currentCamera.fy - previous.fy
            local dfz = currentCamera.fz - previous.fz
            local rotationRight = dot3(dfx, dfy, dfz, currentCamera.rx, currentCamera.ry, currentCamera.rz)
            local rotationUp = dot3(dfx, dfy, dfz, currentCamera.ux, currentCamera.uy, currentCamera.uz)
            local tx = dot3(dx, dy, dz, currentCamera.rx, currentCamera.ry, currentCamera.rz)
            local ty = dot3(dx, dy, dz, currentCamera.ux, currentCamera.uy, currentCamera.uz)
            forwardMotion = dot3(dx, dy, dz, currentCamera.fx, currentCamera.fy, currentCamera.fz)
            motion = { rotationRight, rotationUp, tx, ty }
            currentJitterDelta = {
                (jitter[1] - P.previousJitter[1]) / math.max(P.screenWidth, 1),
                (jitter[2] - P.previousJitter[2]) / math.max(P.screenHeight, 1)
            }
        end
    end

    return motion, forwardMotion, currentJitterDelta, historyValid
end

local function chooseWorkTarget(current)
    if current == P.pool.workA then
        return "workB"
    end
    return "workA"
end

local function passValues(current, depthCurrent)
    return {
        SceneTexture = current,
        DepthTexture = depthCurrent,
        TexelSize = { 1 / math.max(P.internalWidth, 1), 1 / math.max(P.internalHeight, 1) },
        UseDepth = P.depthReady and 1 or 0
    }
end

local function drawDepth(depthTarget, width, height)
    if not P.depthReady then
        return false
    end
    local shader = P.shaders.depth
    setValue(shader, "FarPlane", AR.Config.farPlaneApproximation)
    return drawToTarget("depth", depthTarget, shader, width, height, nil)
end

local function drawDebug(current, depthCurrent, depthPrevious, motionTexture, useDepth)
    if not AR.Debug or not AR.Debug.getModeIndex then
        return false
    end
    local mode = AR.DebugState.mode or "off"
    if mode == "off" then
        return false
    end

    local debugInput = current
    local depthActive = useDepth == 1
    if mode == "ssao" and depthActive and P.shaderUsable.ssao and isValidElement(P.shaders.ssao) then
        local target = P.pool[chooseWorkTarget(current)]
        local values = {
            SceneTexture = current, DepthTexture = depthCurrent,
            NoiseTexture = P.blueNoise or P.screenSource,
            TexelSize = { 1 / P.internalWidth, 1 / P.internalHeight },
            NoiseScale = getNoiseScale(),
            AORadius = 2.0, AOStrength = tonumber(AR.State.strengths.ssao) or 0.12,
            UseDepth = 1, DebugOutput = 1
        }
        if P.shaderUsable.ssao and drawToTarget("ssao_debug", target, P.shaders.ssao, P.internalWidth, P.internalHeight, values) then
            debugInput = target
        end
    elseif mode == "ssr" and depthActive and P.shaderUsable.ssr and isValidElement(P.shaders.ssr) then
        local camera = readCamera()
        local values = {
            SceneTexture = current, DepthTexture = depthCurrent,
            RayNoiseTexture = P.samplingNoise or P.blueNoise or P.screenSource,
            NoiseScale = getNoiseScale(),
            TexelSize = { 1 / P.internalWidth, 1 / P.internalHeight },
            FarPlane = AR.Config.farPlaneApproximation,
            FocalScale = camera and { camera.focalX, camera.focalY } or { 0.7, 1.2 },
            RayLength = 42.0, Thickness = 2.8,
            SSRStrength = tonumber(AR.State.strengths.ssr) or 0.045,
            UseDepth = 1, DebugOutput = 1
        }
        local target = P.pool[chooseWorkTarget(current)]
        if P.shaderUsable.ssr and drawToTarget("ssr_debug", target, P.shaders.ssr, P.internalWidth, P.internalHeight, values) then
            debugInput = target
        end
    end

    local shader = P.shaders.debug
    if not isValidElement(shader) or not P.shaderUsable.debug then
        return false
    end
    local modeIndex = AR.Debug.getModeIndex(mode)
    local values = {
        SceneTexture = debugInput,
        HistoryTexture = P.pool["history" .. tostring(P.historyIndex)],
        CurrentDepth = depthCurrent,
        PreviousDepth = depthPrevious,
        MotionTexture = motionTexture or P.pool.motion,
        TexelSize = { 1 / math.max(P.internalWidth, 1), 1 / math.max(P.internalHeight, 1) },
        DebugMode = modeIndex,
        UseDepth = useDepth,
        HistoryValid = P.historyValid and 1 or 0,
        MotionEnabled = motionTexture and 1 or 0
    }
    for name, value in pairs(values) do
        if value ~= nil then
            setValue(shader, name, value)
        end
    end
    return drawFullscreenToScreen(shader, P.screenWidth, P.screenHeight)
end

local function applyOptionalPass(name, current, depthCurrent, extraValues)
    local targetName = chooseWorkTarget(current)
    local values = passValues(current, depthCurrent)
    if extraValues then
        for key, value in pairs(extraValues) do
            values[key] = value
        end
    end
    if runPass(name, targetName, P.internalWidth, P.internalHeight, values) then
        return P.pool[targetName], true
    end
    return current, false
end

local function updateExposure(current, deltaSeconds, writeIndex)
    if not AR.State.features.toneMapping or not AR.State.features.autoExposure or not P.shaderUsable.luminance then
        return nil
    end
    local readIndex = P.exposureIndex
    local previous = P.pool["exposure" .. tostring(readIndex)]
    local targetName = "exposure" .. tostring(writeIndex)
    local values = {
        SceneTexture = current,
        PreviousExposure = previous,
        PreviousValid = P.exposureValid and 1 or 0,
        AdaptRate = clamp((tonumber(deltaSeconds) or 0.016) * 1.1, 0.01, 0.08)
    }
    if runPass("luminance", targetName, 1, 1, values) then
        P.exposureIndex = writeIndex
        P.exposureValid = true
        P.lastPassNames[#P.lastPassNames + 1] = "luminance"
        return P.pool[targetName]
    end
    return nil
end

local function renderFrame()
    P.lastPassNames = {}
    if AR.Performance then
        AR.Performance.setPipelineSubmitTime(0, 0)
    end
    if not AR.State.enabled then
        P.historyValid = false
        return
    end

    local width, height = guiGetScreenSize()
    width, height = math.max(2, math.floor(width)), math.max(2, math.floor(height))
    local dimensionsChanged = width ~= P.screenWidth or height ~= P.screenHeight
    if not P.reconfigureReason and not dimensionsChanged and not P.ready and getTickCount() < (P.retryAfterTick or 0) then
        return
    end
    if P.reconfigureReason or dimensionsChanged or not P.ready then
        local reason = P.reconfigureReason or (width ~= P.screenWidth or height ~= P.screenHeight) and "display resolution changed" or "initialization"
        P.reconfigureReason = nil
        if not reconfigurePool(reason) then
            return
        end
    end
    if not P.ready or not isValidElement(P.screenSource) or not P.pool then
        return
    end

    if not dxUpdateScreenSource(P.screenSource, true) then
        if not P.lastCaptureWarning then
            AR.log("dxUpdateScreenSource failed; this frame is left untouched rather than compositing stale screen data.", 2)
            P.lastCaptureWarning = true
        end
        P.historyValid = false
        return
    end
    P.lastCaptureWarning = false

    local submissionStart = getTickCount()
    local passCount = 0
    P.lastPassNames = {}
    local writeIndex = 1 - P.historyIndex
    local historyRead = P.pool["history" .. tostring(P.historyIndex)]
    local historyWrite = P.pool["history" .. tostring(writeIndex)]
    local depthCurrent = P.pool["depth" .. tostring(writeIndex)]
    local depthPrevious = P.pool["depth" .. tostring(P.historyIndex)]
    local deltaSeconds = (AR.Performance and AR.Performance.averageFrameMs or 16.7) / 1000
    local jitter = getFrameJitter()
    local camera = readCamera()
    local cameraMotion, forwardMotion, jitterDelta, historyUsable = updateCameraMotion(camera, jitter)

    local depthFrameReady = P.depthReady and drawDepth(depthCurrent, P.internalWidth, P.internalHeight)
    local useDepth = depthFrameReady and 1 or 0
    if depthFrameReady then
        P.lastPassNames[#P.lastPassNames + 1] = "depth"
        passCount = passCount + 1
    end

    local coreValues = {
        SceneTexture = P.screenSource,
        SourceTexelSize = { 1 / P.screenWidth, 1 / P.screenHeight },
        ScaleFactor = P.actualScale,
        Jitter = jitter
    }
    local current
    if runPass("core", "workA", P.internalWidth, P.internalHeight, coreValues) then
        current = P.pool.workA
        P.lastPassNames[#P.lastPassNames + 1] = P.shaderUsable.core and "scene_capture_downsample" or "scene_capture_compatibility_copy"
        passCount = passCount + 1
    else
        -- Copy the unprocessed screen source to the internal target if the pixel technique fell back.
        local fallbackValues = { SceneTexture = P.screenSource }
        if drawToTarget("core_copy", P.pool.workA, P.shaders.core, P.internalWidth, P.internalHeight, fallbackValues) then
            current = P.pool.workA
            P.lastPassNames[#P.lastPassNames + 1] = "scene_capture_copy"
            passCount = passCount + 1
        else
            P.historyValid = false
            if AR.Performance then
                AR.Performance.setPipelineSubmitTime(getTickCount() - submissionStart, #P.lastPassNames)
            end
            return
        end
    end

    local motionTexture = P.pool.motion
    if AR.State.features.temporal and P.shaderUsable.motion then
        local motionValues = {
            DepthTexture = depthCurrent,
            TexelSize = { 1 / P.internalWidth, 1 / P.internalHeight },
            FarPlane = AR.Config.farPlaneApproximation,
            UseDepth = useDepth,
            CameraMotion = cameraMotion,
            CameraMotionForward = forwardMotion,
            FocalScale = camera and { camera.focalX, camera.focalY } or { 0.7, 1.2 },
            JitterDeltaUV = jitterDelta
        }
        if runPass("motion", "motion", P.internalWidth, P.internalHeight, motionValues) then
            motionTexture = P.pool.motion
            P.lastPassNames[#P.lastPassNames + 1] = "motion_estimation"
            passCount = passCount + 1
        else
            motionTexture = nil
        end
    else
        motionTexture = nil
    end

    if AR.State.features.taa and AR.Performance.getFeatureAllowed("taa") and P.shaderUsable.taa then
        local targetName = chooseWorkTarget(current)
        local values = {
            SceneTexture = current,
            DepthTexture = depthCurrent,
            TexelSize = { 1 / P.internalWidth, 1 / P.internalHeight },
            UseDepth = useDepth,
            EdgeThreshold = 0.055,
            EdgeStrength = 0.24
        }
        if runPass("taa", targetName, P.internalWidth, P.internalHeight, values) then
            current = P.pool[targetName]
            P.lastPassNames[#P.lastPassNames + 1] = "edge_aa"
            passCount = passCount + 1
        end
    end

    -- SSR is resolved before temporal accumulation so the history buffer can
    -- stabilize its frame-to-frame ray-march result. It remains depth-gated.
    if AR.State.features.ssr and AR.Performance.getFeatureAllowed("ssr") and useDepth == 1 and P.shaderUsable.ssr then
        local values = {
            SceneTexture = current,
            DepthTexture = depthCurrent,
            RayNoiseTexture = P.samplingNoise or P.blueNoise or P.screenSource,
            NoiseScale = getNoiseScale(),
            TexelSize = { 1 / P.internalWidth, 1 / P.internalHeight },
            FarPlane = AR.Config.farPlaneApproximation,
            FocalScale = camera and { camera.focalX, camera.focalY } or { 0.7, 1.2 },
            RayLength = 42.0,
            Thickness = 2.8,
            SSRStrength = tonumber(AR.State.strengths.ssr) or 0.045,
            UseDepth = 1,
            DebugOutput = 0
        }
        if runPass("ssr", "ssrResult", P.internalWidth, P.internalHeight, values) then
            current = P.pool.ssrResult
            P.lastPassNames[#P.lastPassNames + 1] = "screen_space_reflection"
            passCount = passCount + 1
        end
    end

    -- Resolve depth-based shading before temporal accumulation so the history
    -- can stabilize its frame-to-frame estimates along with SSR.
    if AR.State.features.ssao and AR.Performance.getFeatureAllowed("ssao") and useDepth == 1 and P.shaderUsable.ssao then
        local values = {
            SceneTexture = current,
            DepthTexture = depthCurrent,
            NoiseTexture = P.blueNoise or P.screenSource,
            TexelSize = { 1 / P.internalWidth, 1 / P.internalHeight },
            NoiseScale = getNoiseScale(),
            AORadius = 2.0,
            AOStrength = tonumber(AR.State.strengths.ssao) or 0.12,
            UseDepth = 1,
            DebugOutput = 0
        }
        if runPass("ssao", "ssaoResult", P.internalWidth, P.internalHeight, values) then
            current = P.pool.ssaoResult
            P.lastPassNames[#P.lastPassNames + 1] = "ssao_approximation"
            passCount = passCount + 1
        end
    end

    if AR.State.features.shadowEnhancement and AR.Performance.getFeatureAllowed("shadowEnhancement") and useDepth == 1 and P.shaderUsable.shadow then
        local updated, ran = applyOptionalPass("shadow", current, depthCurrent, {
            ShadowStrength = tonumber(AR.State.strengths.shadow) or 0.03,
            UseDepth = 1
        })
        current = updated
        if ran then
            P.lastPassNames[#P.lastPassNames + 1] = "contact_shadow_approximation"
            passCount = passCount + 1
        end
    end

    local temporalEnabled = AR.State.features.temporal and AR.Performance.getFeatureAllowed("temporal") and P.shaderUsable.temporal
    if temporalEnabled then
        local temporalValues = {
            CurrentTexture = current,
            HistoryTexture = historyRead,
            CurrentDepth = depthCurrent,
            PreviousDepth = depthPrevious,
            MotionTexture = motionTexture or depthCurrent,
            TexelSize = { 1 / P.internalWidth, 1 / P.internalHeight },
            UseDepth = useDepth,
            HistoryValid = historyUsable and 1 or 0,
            MotionEnabled = motionTexture and 1 or 0,
            GlobalMotion = {
                cameraMotion[1] * (camera and camera.focalX or 0.7) + jitterDelta[1],
                -cameraMotion[2] * (camera and camera.focalY or 1.2) + jitterDelta[2],
                0, 0
            },
            HistoryWeight = tonumber(AR.State.strengths.temporal) or 0.84,
            DepthThreshold = 0.025,
            LumaThreshold = 0.10
        }
        if runPass("temporal", "history" .. tostring(writeIndex), P.internalWidth, P.internalHeight, temporalValues) then
            current = historyWrite
            P.lastPassNames[#P.lastPassNames + 1] = "temporal_reconstruction"
            passCount = passCount + 1
            P.historyValid = true
            P.historyIndex = writeIndex
        else
            P.historyValid = false
        end
    else
        P.historyValid = false
    end

    if AR.State.features.reconstruction and AR.Performance.getFeatureAllowed("reconstruction") and P.shaderUsable.reconstruction then
        local updated, ran = applyOptionalPass("reconstruction", current, depthCurrent, {
            DetailStrength = tonumber(AR.State.strengths.detail) or 0.10,
            UseDepth = useDepth
        })
        current = updated
        if ran then
            P.lastPassNames[#P.lastPassNames + 1] = "detail_reconstruction"
            passCount = passCount + 1
        end
    end

    if AR.State.features.sharpen and AR.Performance.getFeatureAllowed("sharpen") and P.shaderUsable.sharpen then
        local updated, ran = applyOptionalPass("sharpen", current, depthCurrent, {
            SharpenStrength = tonumber(AR.State.strengths.sharpen) or 0.08,
            UseDepth = useDepth
        })
        current = updated
        if ran then
            local chosenSharpenTechnique = lowerString(P.shaderTechnique.sharpen)
            P.lastPassNames[#P.lastPassNames + 1] = chosenSharpenTechnique == "compatibility"
                and "detail_recovery_compatibility" or "depth_aware_detail_recovery"
            passCount = passCount + 1
        end
    end

    local exposureTexture
    local exposureWriteIndex = 1 - P.exposureIndex
    exposureTexture = updateExposure(current, deltaSeconds, exposureWriteIndex)
    if exposureTexture then
        passCount = passCount + 1
    end

    if AR.State.features.toneMapping and P.shaderUsable.tonemap then
        local targetName = chooseWorkTarget(current)
        local values = {
            SceneTexture = current,
            ExposureTexture = exposureTexture or P.pool["exposure" .. tostring(P.exposureIndex)],
            UseAutoExposure = (AR.State.features.autoExposure and P.exposureValid) and 1 or 0,
            ManualExposure = tonumber(AR.State.strengths.manualExposure) or 1.0,
            ToneStrength = tonumber(AR.State.strengths.toneMap) or 0.10,
            ToneMapMode = 1
        }
        if runPass("tonemap", targetName, P.internalWidth, P.internalHeight, values) then
            current = P.pool[targetName]
            P.lastPassNames[#P.lastPassNames + 1] = "ldr_tone_mapping"
            passCount = passCount + 1
        end
    end

    local upscaleValues = {
        SceneTexture = current,
        DepthTexture = depthCurrent,
        SourceTexelSize = { 1 / P.internalWidth, 1 / P.internalHeight },
        DepthTexelSize = { 1 / P.internalWidth, 1 / P.internalHeight },
        UseDepth = useDepth,
        ReconstructionEnabled = AR.State.features.superResolution and 1 or 0,
        EdgeStrength = 0.75
    }
    local outputOK = runPass("superResolution", "output", P.screenWidth, P.screenHeight, upscaleValues)
    if outputOK then
        local chosenUpscaleTechnique = lowerString(P.shaderTechnique.superResolution)
        local highQualityUpscale = AR.State.features.superResolution and P.shaderUsable.superResolution
            and chosenUpscaleTechnique ~= "compatibility"
        P.lastPassNames[#P.lastPassNames + 1] = highQualityUpscale and "edge_aware_super_resolution" or "native_resolution_resample"
        passCount = passCount + 1
    else
        -- The compatibility technique in super_resolution.fx is a plain texture copy.
        P.historyValid = false
        if AR.Performance then
            AR.Performance.setPipelineSubmitTime(getTickCount() - submissionStart, #P.lastPassNames)
        end
        return
    end

    local debugDrawn = false
    if AR.DebugState.mode ~= "off" and AR.DebugState.mode ~= nil then
        debugDrawn = drawDebug(current, depthCurrent, depthPrevious, motionTexture, useDepth)
    end

    if debugDrawn then
        P.lastPassNames[#P.lastPassNames + 1] = "debug_visualization"
        passCount = passCount + 1
    else
        local finalShader = P.shaders.finalComposite
        local compositeDrawn = false
        if isValidElement(finalShader) then
            setValue(finalShader, "SceneTexture", P.pool.output)
            local colorEnabled = AR.State.features.colorManagement == true
            setValue(finalShader, "ExposureEV", colorEnabled and (tonumber(AR.State.strengths.exposureEV) or 0.0) or 0.0)
            setValue(finalShader, "Contrast", colorEnabled and (tonumber(AR.State.strengths.contrast) or 1.0) or 1.0)
            setValue(finalShader, "Saturation", colorEnabled and (tonumber(AR.State.strengths.saturation) or 1.0) or 1.0)
            setValue(finalShader, "Temperature", colorEnabled and (tonumber(AR.State.strengths.temperature) or 0.0) or 0.0)
            compositeDrawn = drawFullscreenToScreen(finalShader, P.screenWidth, P.screenHeight)
        end
        local compositeName = "final_composite"
        if not compositeDrawn then
            compositeDrawn = drawFullscreenToScreen(P.shaders.superResolution, P.screenWidth, P.screenHeight)
            compositeName = "final_composite_copy_fallback"
        end
        if compositeDrawn then
            P.lastPassNames[#P.lastPassNames + 1] = compositeName
            passCount = passCount + 1
        else
            P.historyValid = false
        end
    end

    P.previousJitter = jitter
    P.previousCamera = camera
    P.frameIndex = P.frameIndex + 1
    local totalSubmit = getTickCount() - submissionStart
    if AR.Performance then
        AR.Performance.setPipelineSubmitTime(totalSubmit, passCount)
    end
end

function P.setFeature(name, enabled)
    if type(name) ~= "string" then
        return false
    end
    if AR.State.features[name] == nil then
        return false
    end
    AR.State.features[name] = enabled == true
    if name == "temporal" or name == "taa" or name == "superResolution" then
        P.invalidateHistory("feature '" .. name .. "' changed")
    end
    if name == "vehicleResponse" or name == "materialEnhancement" then
        if AR.Materials then
            AR.Materials.setFeature(name, enabled)
        end
    end
    return true
end

function P.setEnabled(enabled)
    AR.State.enabled = enabled == true
    P.invalidateHistory("master switch changed")
    if AR.Materials and AR.Materials.started then
        AR.Materials.syncWorldMaterials()
        AR.Materials.syncVehicle()
    end
    return true
end

function P.getStats()
    return {
        ready = P.ready == true,
        width = P.screenWidth,
        height = P.screenHeight,
        internalWidth = P.internalWidth,
        internalHeight = P.internalHeight,
        requestedScale = AR.State.resolutionScale,
        actualScale = P.ready and P.actualScale or AR.State.resolutionScale,
        depthReady = P.depthReady,
        temporalValid = P.historyValid,
        passes = P.lastPassNames or {},
        shaderUsable = P.shaderUsable,
        shaderTechnique = P.shaderTechnique
    }
end

local function handleDeviceRestore()
    P.invalidateHistory("device restore/minimize")
    if AR.Performance then
        AR.Performance.refreshDeviceInfo(true)
    end

    destroyPool(P.pool)
    P.pool = nil
    P.ready = false
    destroyScreenSource()
    for _, shader in pairs(P.shaders) do
        safeDestroy(shader)
    end
    P.shaders = {}
    P.shaderUsable = {}
    P.shaderTechnique = {}
    safeDestroy(P.blueNoise)
    safeDestroy(P.samplingNoise)
    P.blueNoise = nil
    P.samplingNoise = nil
    P.depthReady = false
    P.retryAfterTick = 0
    P.lastCaptureWarning = false
    P.lastTargetWarning = false

    createShaders()
    P.requestReconfigure("device restore")
    if AR.Materials and AR.Materials.started then
        AR.Materials.syncWorldMaterials()
        AR.Materials.syncVehicle()
    end
end

function P.start()
    if P.started then
        return
    end
    P.started = true
    createShaders()
    P.requestReconfigure("resource start")
    addEventHandler("onClientHUDRender", root, renderFrame)
    addEventHandler("onClientRestore", root, handleDeviceRestore)
end

function P.stop()
    if not P.started then
        return
    end
    removeEventHandler("onClientHUDRender", root, renderFrame)
    removeEventHandler("onClientRestore", root, handleDeviceRestore)
    destroyPool(P.pool)
    P.pool = nil
    destroyScreenSource()
    for _, shader in pairs(P.shaders) do
        safeDestroy(shader)
    end
    P.shaders = {}
    P.shaderUsable = {}
    P.shaderTechnique = {}
    safeDestroy(P.blueNoise)
    safeDestroy(P.samplingNoise)
    P.blueNoise = nil
    P.samplingNoise = nil
    P.started = false
    P.ready = false
end
