-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: CONFIGURATION
-- ============================================================================

-- All runtime tuning lives here.  Values are deliberately conservative because
-- processLineOfSight and client-side ped simulation can become expensive fast.
Config = {
    version = "1.0.0",

    debug = false,
    maxNPCs = 200,

    logging = {
        enabled = true,
        debug = false,
        rateLimitMs = 1500,
    },

    nodes = {
        manifestPath = "data/gta_nodes/manifest.json",
        areaSize = 750,
        worldMin = -3000,
        areasPerAxis = 8,
        nearestCacheCellSize = 24,
        nearestCacheDistance = 18,
        nearestSearchCellRings = 8,
        spatialCellSize = 64,
        preloadAreaRadius = 1,
        unloadDistance = 450,
        unloadAfterMs = 30000,
        maxLoadedAreas = 14,
        nodeLoadTimeoutMs = 12000,
    },

    pathfinding = {
        algorithm = "A*",
        maxIterations = 12000,
        operationsPerTick = 650,
        operationsPerRequest = 96,
        heuristicWeight = 0.98,
        repathCooldownMs = 1000,
        blockedRepathCooldownMs = 1500,
        retryDelayMs = 1250,
        maxRetries = 4,
        cacheTtlMs = 45000,
        cacheMaxEntries = 256,
        maxPathNodes = 4096,
        nodeArrivalDistance = 1.35,
        goalArrivalDistance = 2.25,
        smoothing = {
            enabled = true,
            maxVisibilityChecks = 32,
            maxSegmentDistance = 18,
            maxVerticalDelta = 2.75,
            maxDistanceFromPlayer = 180,
        },
    },

    avoidance = {
        enabled = true,
        rayStartHeight = 0.72,
        rayLength = 2.4,
        sideRayLength = 1.55,
        forwardLeftAngle = 32,
        forwardRightAngle = -32,
        sideAngle = 76,
        nearIntervalMs = 125,
        mediumIntervalMs = 250,
        farIntervalMs = 600,
        dynamicRange = 3.2,
        dynamicWeight = 1.25,
        wallWeight = 1.7,
        slowDistance = 1.75,
        majorObstacleDistance = 0.78,
        majorObstaclePersistMs = 850,
        maximumForce = 1.6,
    },

    movement = {
        walkSpeed = 1.0,
        fastWalkSpeed = 1.28,
        runSpeed = 1.7,
        defaultSpeed = 1.0,
        allowRun = false,
        acceleration = 2.7,
        deceleration = 4.2,
        maxTurnDegreesPerSecond = 220,
        turnSlowdownStart = 35,
        turnStopAt = 105,
        turnControlThreshold = 16,
        rotationEpsilon = 0.35,
        finalApproachDistance = 5.5,
        finalApproachLineOfSight = true,
        animationMinRate = 0.55,
        animationMaxRate = 1.15,
    },

    stuck = {
        sampleIntervalMs = 700,
        windowMs = 3000,
        minimumMovement = 0.55,
        localRecoveryMs = 750,
        alternateRecoveryMs = 1100,
        maxRecoveries = 3,
        loopHistorySize = 18,
        loopVisitsBeforeRepath = 3,
        waitAfterFailureMs = 1500,
        -- This resource intentionally never teleports a ped during recovery.
        -- A project may opt in only after implementing its own safe-spawn policy.
        allowEmergencyTeleport = false,
    },

    wandering = {
        defaultRadius = 300,
        minRadius = 35,
        maxRadius = 900,
        idleMinMs = 1100,
        idleMaxMs = 4200,
    },

    performance = {
        nearDistance = 50,
        mediumDistance = 150,
        farDistance = 300,
        nearTickMs = 50,      -- 20 Hz
        mediumTickMs = 100,   -- 10 Hz
        farTickMs = 350,      -- ~3 Hz
        sleepingTickMs = 1000,
        maxAgentsPerFrame = 32,
        areaGcTickMs = 5000,
        profilerWindowMs = 1000,
    },

    networking = {
        ownerDistance = 90, -- MTA ped sync range is approximately 100 units.
        ownerUpdateMs = 1000,
        persistSyncer = false,
        reportIntervalMs = 1000,
        clientEventMinIntervalMs = 500,
        snapshotMaxNPCs = 250,
    },

    security = {
        commandACLRight = "function.kickPlayer",
        maxSpawnPerCommand = 25,
        maxWanderDestinationDistance = 950,
        worldCoordinateLimit = 6000,
    },

    debugDraw = {
        maxDistance = 120,
        nodeRadius = 0.16,
        lineWidth = 2,
        showProfiler = true,
    },
}
