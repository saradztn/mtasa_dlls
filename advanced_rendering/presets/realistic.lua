local AR = AdvancedRendering
AR.Presets.REALISTIC = {
    label = "REALISTIC", quality = "HIGH", scale = 0.85,
    features = {
        temporal = true, taa = true, reconstruction = true, superResolution = true,
        ssao = true, ssr = false, shadowEnhancement = false, vehicleResponse = true,
        materialEnhancement = false, sharpen = true, toneMapping = false,
        autoExposure = false, colorManagement = true
    },
    strengths = {
        temporal = 0.84, detail = 0.095, ssao = 0.105, ssr = 0.035,
        shadow = 0.02, vehicle = 0.07, sharpen = 0.075, toneMap = 0.08,
        manualExposure = 1.0, exposureEV = 0.0, contrast = 1.0,
        saturation = 1.0, temperature = 0.0
    }
}
