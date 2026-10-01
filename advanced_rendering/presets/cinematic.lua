local AR = AdvancedRendering
AR.Presets.CINEMATIC = {
    label = "CINEMATIC", quality = "HIGH", scale = 0.75,
    features = {
        temporal = true, taa = true, reconstruction = true, superResolution = true,
        ssao = true, ssr = true, shadowEnhancement = true, vehicleResponse = true,
        materialEnhancement = false, sharpen = true, toneMapping = true,
        autoExposure = true, colorManagement = true
    },
    strengths = {
        temporal = 0.82, detail = 0.09, ssao = 0.16, ssr = 0.045,
        shadow = 0.025, vehicle = 0.08, sharpen = 0.075, toneMap = 0.10,
        manualExposure = 1.0, exposureEV = 0.0, contrast = 1.01,
        saturation = 0.99, temperature = 0.0
    }
}
