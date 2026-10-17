--[[
  NextGenPoliceDepartment - Shared Configuration (Server + Client)
  Photorealistic Golden-Hour, Wet-Surface PBR & 4K Spatial Upscaling Edition
  Target Hardware Profile: AMD Radeon RX 580 2048SP | Ryzen 5 3600X | 16 GB RAM
]]

NGPD_CONFIG = {
    -- Default world transform (overridden by persisted server setting "origin")
    origin = { x = 177.0, y = 2514.5, z = 16.2, rz = 0.0 },
    interior = 0,
    dimension = 0,

    -- Default quality preset ("performance" | "balanced" | "high" | "ultra" | "upscaling_4k"
    -- as well as backward-compatible aliases "low" | "medium")
    defaultQuality = "high",

    qualityProfiles = {
        -- Legacy & Performance Presets
        low = {
            label = "Performance (Low)",
            txd = "low",            -- 256 px DXT1/DXT3 TXD (2.7 MB)
            shaders = false,        -- Fixed-function prelit GTA rendering
            maps = nil,
            shaderDistance = 0,
            normalScale = 0.5,
            reflectScale = 0.4,
            sunGlare = 0.8,
            bloomIntensity = 0.5,
            shadowContrast = 0.9,
            puddleScale = 0.6,
            windStrength = 0.0,
            lampCoronas = 0,
            wetness = false,
            weatherPresets = true,
            drawDistanceScale = 0.85,
            upscalerEnabled = false,
            upscalerPreset = "performance",
            upscalerScale = 0.50,
            upscalerSharpness = 0.80,
        },
        performance = {
            label = "Performance",
            txd = "low",
            shaders = true,
            maps = "medium",
            shaderDistance = 55,
            normalScale = 0.65,
            reflectScale = 0.60,
            sunGlare = 0.95,
            bloomIntensity = 0.75,
            shadowContrast = 0.95,
            puddleScale = 0.80,
            windStrength = 0.50,
            lampCoronas = 8,
            wetness = true,
            weatherPresets = true,
            drawDistanceScale = 0.90,
            upscalerEnabled = false,
            upscalerPreset = "performance",
            upscalerScale = 0.50,
            upscalerSharpness = 0.80,
        },
        medium = {
            label = "Balanced (Medium)",
            txd = "med",            -- 512 px TXD (7.8 MB)
            shaders = true,
            maps = "medium",        -- <=512 px DXT5 normal/surface DDS maps
            shaderDistance = 95,
            normalScale = 0.85,
            reflectScale = 0.85,
            sunGlare = 1.10,
            bloomIntensity = 0.95,
            shadowContrast = 1.00,
            puddleScale = 0.95,
            windStrength = 0.85,
            lampCoronas = 20,
            wetness = true,
            weatherPresets = true,
            drawDistanceScale = 1.05,
            upscalerEnabled = false,
            upscalerPreset = "balanced",
            upscalerScale = 0.59,
            upscalerSharpness = 0.76,
        },
        balanced = {
            label = "Balanced",
            txd = "med",
            shaders = true,
            maps = "medium",
            shaderDistance = 95,
            normalScale = 0.85,
            reflectScale = 0.85,
            sunGlare = 1.10,
            bloomIntensity = 0.95,
            shadowContrast = 1.00,
            puddleScale = 0.95,
            windStrength = 0.85,
            lampCoronas = 20,
            wetness = true,
            weatherPresets = true,
            drawDistanceScale = 1.05,
            upscalerEnabled = false,
            upscalerPreset = "balanced",
            upscalerScale = 0.59,
            upscalerSharpness = 0.76,
        },
        high = {
            label = "High Quality",
            txd = "high",           -- 1024 px TXD (10.5 MB)
            shaders = true,
            maps = "high",          -- Full resolution 1024 px DXT5nm normal & surface maps
            shaderDistance = 165,
            normalScale = 1.05,
            reflectScale = 1.15,
            sunGlare = 1.25,
            bloomIntensity = 1.05,
            shadowContrast = 1.05,
            puddleScale = 1.05,
            windStrength = 1.00,
            lampCoronas = 40,
            wetness = true,
            weatherPresets = true,
            drawDistanceScale = 1.25,
            upscalerEnabled = false,
            upscalerPreset = "quality",
            upscalerScale = 0.67,
            upscalerSharpness = 0.72,
        },
        ultra = {
            label = "Ultra (Golden-Hour Cinema)",
            txd = "high",
            shaders = true,
            maps = "high",
            shaderDistance = 260,
            normalScale = 1.20,
            reflectScale = 1.32,
            sunGlare = 1.40,
            bloomIntensity = 1.18,
            shadowContrast = 1.12,
            puddleScale = 1.18,
            windStrength = 1.10,
            lampCoronas = 40,
            wetness = true,
            weatherPresets = true,
            drawDistanceScale = 1.50,
            upscalerEnabled = false,
            upscalerPreset = "ultra_quality",
            upscalerScale = 0.77,
            upscalerSharpness = 0.65,
        },
        upscaling_4k = {
            label = "4K Upscaling (RX 580 2048SP EASU+RCAS)",
            txd = "high",
            shaders = true,
            maps = "high",
            shaderDistance = 220,
            normalScale = 1.15,
            reflectScale = 1.25,
            sunGlare = 1.35,
            bloomIntensity = 1.12,
            shadowContrast = 1.08,
            puddleScale = 1.12,
            windStrength = 1.00,
            lampCoronas = 40,
            wetness = true,
            weatherPresets = true,
            drawDistanceScale = 1.35,
            upscalerEnabled = true,
            upscalerPreset = "quality", -- 67% internal scale -> 4K UHD (55.2% pixel savings on RX 580)
            upscalerScale = 0.67,
            upscalerSharpness = 0.72,
        },
    },

    -- Golden-Hour Atmospheric Lighting & Sun System configuration
    lighting = {
        defaultWeatherPreset = "goldenhour",
        enableSolarDiscGlare = true,
        solarDiscSize = 4.5,
        sunGlareStrength = 1.25,
        bloomStrength = 1.05,
        shadowContrast = 1.05,
        transitionSeconds = 2.5,
    },

    -- AMD FSR 1.0 Style Spatial 4K Upscaler (EASU + RCAS) configuration
    upscaler = {
        enabledByDefault = false,
        targetWidth = 3840,
        targetHeight = 2160,
        defaultPreset = "quality",
        scaleFactor = 0.67,         -- 0.50 .. 1.00 (50% .. 100%)
        sharpness = 0.72,           -- 0.00 .. 1.00 RCAS sharpening
        edgeSharpness = 1.00,       -- EASU directional gradient strength
        preserveAspectRatio = true, -- Letterbox/pillarbox if display is non-16:9
        showStatusBadge = true,     -- Native-res HUD telemetry indicator
        atmosBloom = 0.35,          -- Screen-space solar glare pass
        presets = {
            performance   = { scale = 0.50, sharpness = 0.80, label = "Performance (50% -> 4K)" },
            balanced      = { scale = 0.59, sharpness = 0.76, label = "Balanced (59% -> 4K)" },
            quality       = { scale = 0.67, sharpness = 0.72, label = "Quality (67% -> 4K)" },
            ultra_quality = { scale = 0.77, sharpness = 0.65, label = "Ultra Quality (77% -> 4K)" },
            native        = { scale = 1.00, sharpness = 0.55, label = "Native 100% + RCAS" },
        },
    },

    -- Door system (server authoritative)
    doors = {
        interactRadius = 2.6,
        cooldownMs = 900,
        doorCooldownMs = 600,
        defaultOpenMs = 1400,
        gateOpenMs = 6000,
        autoCloseMs = {
            exit = 8000, swing = 10000, slide_glass = 6000, security = 7000, cell = 0,
            rollup = 25000, gate = 20000, barrier = 9000,
        },
        vehicleRadius = 9.0,
        vehicleKinds = { gate = true, barrier = true, rollup = true },
        easing = "InOutQuad",
    },

    -- Access groups
    access = {
        public    = { open = true },
        police    = { acl = { "Police", "Admin", "SuperModerator", "Moderator" }, teams = { "Police", "LSPD", "SFPD", "LVPD", "Sheriff" }, data = { "ngpd.police" } },
        detention = { acl = { "Police", "Admin", "SuperModerator" }, teams = { "Police", "LSPD", "SFPD", "LVPD", "Sheriff" }, data = { "ngpd.detention" } },
        evidence  = { acl = { "Police", "Admin", "SuperModerator" }, teams = { "Police", "LSPD", "SFPD", "LVPD", "Sheriff" }, data = { "ngpd.evidence" } },
        command   = { acl = { "Admin", "SuperModerator" }, teams = {}, data = { "ngpd.command" } },
        admin     = { acl = { "Admin" }, teams = {}, data = {} },
    },
    adminGroup = "admin",
    teleportAccess = "admin",

    -- Elevators
    elevatorRadius = 1.6,
    elevatorCooldownMs = 2000,

    -- Decorative police vehicles
    spawnVehicles = true,

    -- Wet surfaces (client)
    wet = {
        defaultWetness = 0.74,      -- Golden-hour post-rain wet pavement default
        riseRate = 1 / 45,
        dryRate = 1 / 240,
        dryRateNight = 1 / 480,
        lightRain = 0.05,
        heavyRain = 0.45,
        updateMs = 250,
    },

    presetCommand = "ngpd_weather",
}

NGPD_CONFIG.accessAliases = {
    public = "public",
    police = "police",
    detention = "detention",
    evidence = "evidence",
    command = "command",
}
