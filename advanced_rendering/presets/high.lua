local AR = AdvancedRendering
AR.Presets.HIGH = {
    label = "HIGH", quality = "HIGH", scale = 0.85,
    features = {
        temporal = true, taa = true, reconstruction = true, superResolution = true,
        ssao = true, ssr = false, shadowEnhancement = false, vehicleResponse = true,
        materialEnhancement = false, sharpen = true, toneMapping = false,
        autoExposure = false, colorManagement = true
    },
    strengths = {
        temporal = 0.84, detail = 0.10, ssao = 0.12, ssr = 0.045,
        shadow = 0.025, vehicle = 0.075, sharpen = 0.085, toneMap = 0.10,
        manualExposure = 1.0, exposureEV = 0.0, contrast = 1.0,
        saturation = 1.0, temperature = 0.0
    }
}
