local AR = AdvancedRendering
AR.Presets.BALANCED = {
    label = "BALANCED", quality = "MEDIUM", scale = 0.75,
    features = {
        temporal = true, taa = true, reconstruction = true, superResolution = true,
        ssao = true, ssr = false, shadowEnhancement = false, vehicleResponse = true,
        materialEnhancement = false, sharpen = true, toneMapping = false,
        autoExposure = false, colorManagement = true
    },
    strengths = {
        temporal = 0.82, detail = 0.08, ssao = 0.09, ssr = 0.03,
        shadow = 0.02, vehicle = 0.06, sharpen = 0.07, toneMap = 0.08,
        manualExposure = 1.0, exposureEV = 0.0, contrast = 1.0,
        saturation = 1.0, temperature = 0.0
    }
}
