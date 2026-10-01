local AR = AdvancedRendering
AR.Presets["ULTRA QUALITY"] = {
    label = "ULTRA QUALITY", quality = "ULTRA", scale = 1.00,
    features = {
        temporal = true, taa = true, reconstruction = true, superResolution = true,
        ssao = true, ssr = true, shadowEnhancement = true, vehicleResponse = true,
        materialEnhancement = true, sharpen = true, toneMapping = false,
        autoExposure = false, colorManagement = true
    },
    strengths = {
        temporal = 0.86, detail = 0.11, ssao = 0.15, ssr = 0.055,
        shadow = 0.035, vehicle = 0.085, sharpen = 0.08, toneMap = 0.10,
        manualExposure = 1.0, exposureEV = 0.0, contrast = 1.0,
        saturation = 1.0, temperature = 0.0
    }
}
