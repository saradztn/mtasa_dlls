AdvancedRendering = AdvancedRendering or {}
local AR = AdvancedRendering

AR.VERSION = "1.0.0"
AR.Config = {
    defaultPreset = "REALISTIC",
    defaultQuality = "HIGH",
    defaultScale = 0.85,
    scaleSteps = { 1.00, 0.85, 0.75, 0.67, 0.50 },
    minScale = 0.50,
    maxScale = 1.00,
    farPlaneApproximation = 1800.0,
    adaptiveDownThresholdMs = 19.0,
    adaptiveUpThresholdMs = 14.5,
    adaptiveDownHoldMs = 2200,
    adaptiveUpHoldMs = 7000,
    adaptiveCooldownMs = 4500,
    blueNoiseSize = 64,
    debugOverlay = true,
    uiKey = "F10",
    command = "ars",
    debugCommand = "arsdebug",
    qualityProfiles = {
        ULTRA = {
            baseScale = 1.00, minScale = 0.67,
            ssao = true, ssr = true, shadow = true,
            material = true, vehicle = true, temporal = true, taa = true,
            reconstruction = true, superResolution = true, sharpen = true
        },
        HIGH = {
            baseScale = 0.85, minScale = 0.50,
            ssao = true, ssr = false, shadow = false,
            material = true, vehicle = true, temporal = true, taa = true,
            reconstruction = true, superResolution = true, sharpen = true
        },
        MEDIUM = {
            baseScale = 0.75, minScale = 0.50,
            ssao = true, ssr = false, shadow = false,
            material = false, vehicle = true, temporal = true, taa = true,
            reconstruction = true, superResolution = true, sharpen = true
        },
        LOW = {
            baseScale = 0.50, minScale = 0.50,
            ssao = false, ssr = false, shadow = false,
            material = false, vehicle = false, temporal = true, taa = true,
            reconstruction = false, superResolution = false, sharpen = false
        },
        COMPATIBILITY = {
            baseScale = 0.67, minScale = 0.50,
            ssao = false, ssr = false, shadow = false,
            material = false, vehicle = false, temporal = false, taa = true,
            reconstruction = false, superResolution = false, sharpen = false
        }
    },
    materialClasses = {
        -- Patterns are deliberately conservative. GTA texture naming differs between maps.
        road = {
            response = 0.018, roughness = 0.88, tint = { 1.00, 1.00, 1.00 },
            patterns = { "road*", "roads*", "asphalt*" }
        },
        concrete = {
            response = 0.010, roughness = 0.96, tint = { 1.00, 1.00, 1.00 },
            patterns = { "concrete*", "cement*" }
        },
        grass = {
            response = 0.004, roughness = 1.00, tint = { 1.00, 1.00, 1.00 },
            patterns = { "grass*" }
        },
        sand = {
            response = 0.006, roughness = 0.98, tint = { 1.00, 1.00, 1.00 },
            patterns = { "sand*" }
        },
        metal = {
            response = 0.030, roughness = 0.68, tint = { 1.00, 1.00, 1.00 },
            patterns = { "metal*", "steel*", "chrome*" }
        }
    }
}

AR.Presets = AR.Presets or {}
AR.State = {
    enabled = true,
    preset = AR.Config.defaultPreset,
    quality = AR.Config.defaultQuality,
    resolutionScale = AR.Config.defaultScale,
    dynamicResolution = true,
    features = {
        temporal = true,
        taa = true,
        reconstruction = true,
        superResolution = true,
        ssao = true,
        ssr = false,
        shadowEnhancement = false,
        vehicleResponse = true,
        materialEnhancement = false,
        sharpen = true,
        toneMapping = false,
        autoExposure = false,
        colorManagement = true
    },
    strengths = {
        temporal = 0.84,
        detail = 0.10,
        ssao = 0.12,
        ssr = 0.045,
        shadow = 0.035,
        vehicle = 0.075,
        sharpen = 0.085,
        toneMap = 0.12,
        manualExposure = 1.0,
        exposureEV = 0.0,
        contrast = 1.0,
        saturation = 1.0,
        temperature = 0.0
    }
}

AR.DebugState = {
    mode = "off",
    showPanel = false
}

function AR.log(message, level)
    local prefix = "[ARS " .. AR.VERSION .. "] "
    outputDebugString(prefix .. tostring(message), level or 3, 116, 196, 255)
end

function AR.notify(message, r, g, b)
    outputChatBox("[ARS] " .. tostring(message), r or 130, g or 210, b or 255, true)
end

function AR.copyTable(source)
    local result = {}
    if type(source) ~= "table" then
        return result
    end
    for key, value in pairs(source) do
        if type(value) == "table" then
            result[key] = AR.copyTable(value)
        else
            result[key] = value
        end
    end
    return result
end
