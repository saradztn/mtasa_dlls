local AR = AdvancedRendering
AR.Presets.PERFORMANCE = {
    label = "PERFORMANCE", quality = "LOW", scale = 0.50,
    features = {
        temporal = true, taa = true, reconstruction = false, superResolution = true,
        ssao = false, ssr = false, shadowEnhancement = false, vehicleResponse = false,
        materialEnhancement = false, sharpen = true, toneMapping = false,
        autoExposure = false, colorManagement = true
    },
    strengths = {
        temporal = 0.78, detail = 0.05, ssao = 0.0, ssr = 0.0,
        shadow = 0.0, vehicle = 0.0, sharpen = 0.055, toneMap = 0.0,
        manualExposure = 1.0, exposureEV = 0.0, contrast = 1.0,
        saturation = 1.0, temperature = 0.0
    }
}
