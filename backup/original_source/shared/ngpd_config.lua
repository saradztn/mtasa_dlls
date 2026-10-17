--[[
  NextGenPoliceDepartment - shared configuration (server + client).

  World placement
    The whole complex is authored in building-local metres (x east, y north, z up, origin = centre of
    the main entrance axis at ground-floor level).  At runtime every model, door, vehicle and anchor is
    transformed by:  world = origin + Rz(rotation) * local.
    The DEFAULT placement below targets the Verdant Meadows airstrip (runway 27/09 runs from
    (432, 2503, 16) to (-78, 2504, 16)).  It was chosen from published map coordinates and has NOT been
    verified in-game: the 118 m deep site is wider than the 52 m runway, so parts of the site overlap the
    aircraft boneyard objects next to the runway.  No GTA world model is removed by this resource.
    Admins can move the complex with /ngpd_relocate (stands at their position) or /ngpd_setorigin x y z rz;
    the choice is persisted in the resource settings (server-side) and applies to every client.
]]

NGPD_CONFIG = {
    -- default world transform (overridden by the persisted setting "origin")
    origin = { x = 177.0, y = 2514.5, z = 16.2, rz = 0.0 },
    interior = 0,
    dimension = 0,

    -- quality: "low" | "medium" | "high"; clients may change their own with /ngpd_quality
    defaultQuality = "medium",
    qualityProfiles = {
        low = {
            txd = "low",            -- 256 px DXT1/DXT3 TXD (2.5 MB)
            shaders = false,        -- no custom HLSL, plain prelit GTA rendering
            maps = nil,
            shaderDistance = 0,
            lampCoronas = 0,        -- night corona markers
            wetness = false,        -- wet state still tracked, nothing rendered
            weatherPresets = true,
            drawDistanceScale = 0.8,
        },
        medium = {
            txd = "med",            -- 512 px TXD
            shaders = true,
            maps = "medium",        -- <=512 px normal/surface DDS maps (1024 px sources downsampled)
            shaderDistance = 60,    -- per-pixel shading-detail fade end (m); fade starts at 55 %. Shaders have no per-object maxDistance (run #5 popping fix)
            normalScale = 0.7,
            reflectScale = 0.7,
            lampCoronas = 12,
            wetness = true,
            weatherPresets = true,
            drawDistanceScale = 1.0,
        },
        high = {
            txd = "high",           -- 1024 px TXD (downloaded on demand)
            shaders = true,
            maps = "high",          -- full resolution DDS maps (downloaded on demand)
            shaderDistance = 140,
            normalScale = 1.0,
            reflectScale = 1.0,
            lampCoronas = 40,
            wetness = true,
            weatherPresets = true,
            drawDistanceScale = 1.25,
        },
    },

    -- door system (server authoritative)
    doors = {
        interactRadius = 2.6,       -- metres from the door centre (server re-checks)
        cooldownMs = 900,           -- per player
        doorCooldownMs = 600,       -- per door, after a transition ends
        defaultOpenMs = 1400,       -- moveObject duration for hinged/sliding leaves
        gateOpenMs = 6000,          -- large site gates
        autoCloseMs = { exit = 8000, swing = 10000, slide_glass = 6000, security = 7000, cell = 0,
                        rollup = 25000, gate = 20000, barrier = 9000 },
        vehicleRadius = 9.0,        -- gates / barrier / garage may be requested from a vehicle within this range
        vehicleKinds = { gate = true, barrier = true, rollup = true },
        easing = "InOutQuad",
    },

    -- access groups.  A player satisfies a group if ANY rule matches:
    --   acl    : member of one of these ACL groups (works for logged-in accounts)
    --   teams  : on a team with one of these names
    --   data   : element data key that is truthy on the player (e.g. set by a job script)
    -- "public" is always open.  "admin" always grants everything.
    access = {
        public    = { open = true },
        police    = { acl = { "Police", "Admin", "SuperModerator", "Moderator" }, teams = { "Police", "LSPD", "SFPD", "LVPD", "Sheriff" }, data = { "ngpd.police" } },
        detention = { acl = { "Police", "Admin", "SuperModerator" }, teams = { "Police", "LSPD", "SFPD", "LVPD", "Sheriff" }, data = { "ngpd.detention" } },
        evidence  = { acl = { "Police", "Admin", "SuperModerator" }, teams = { "Police", "LSPD", "SFPD", "LVPD", "Sheriff" }, data = { "ngpd.evidence" } },
        command   = { acl = { "Admin", "SuperModerator" }, teams = {}, data = { "ngpd.command" } },
        admin     = { acl = { "Admin" }, teams = {}, data = {} },
    },
    adminGroup = "admin",

    -- /ngpd_tp (teleport to lobby) access group; "public" makes it a convenience command for everyone
    teleportAccess = "admin",

    -- elevators
    elevatorRadius = 1.6,
    elevatorCooldownMs = 2000,

    -- decorative police vehicles (server creates them frozen, locked, damage-proof)
    spawnVehicles = true,

    -- wet surfaces (client)
    wet = {
        riseRate = 1 / 45,          -- wetness per second at full rain
        dryRate = 1 / 240,          -- wetness per second when dry & sunny
        dryRateNight = 1 / 480,
        lightRain = 0.05,           -- getRainLevel thresholds
        heavyRain = 0.45,
        updateMs = 250,
    },

    -- weather/time presets are client-local and only active while a player chooses one
    presetCommand = "ngpd_weather",
}

-- groups each door kind/access maps to (doors carry "access" from the asset builder)
NGPD_CONFIG.accessAliases = { public = "public", police = "police", detention = "detention", evidence = "evidence", command = "command" }
