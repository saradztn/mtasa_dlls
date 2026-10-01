--[[
    spider_sa / config.lua  -  all tunables for the Spider SA resource.

    Shared: the client reads the asset paths, spawning and message options; the
    server only uses spawnDistance and the message language.
]]

SpiderConfig = {
    ---------------------------------------------------------------------
    -- assets (paths are relative to the resource root)
    ---------------------------------------------------------------------
    dffFile = "assets/Dragon_2.5.dff",
    colFile = "assets/Dragon_2.5.col",
    txdFile = "assets/Dragon_2.5.txd",

    -- engineLoadTXD(path, filteringEnabled):
    --   false keeps the filtering mode stored inside the TXD
    --   (FILTER_LINEAR_MIP_LINEAR + wrap) and lets the engine build mipmaps,
    --   true forces point filtering and disables mipmaps -> blocky at distance.
    txdFiltering = false,

    -- Install the model as soon as the resource starts (otherwise it is
    -- installed the first time something is spawned).
    installOnStart = false,

    ---------------------------------------------------------------------
    -- model slot
    ---------------------------------------------------------------------
    -- Preferred path: engineRequestModel("object") allocates a free model ID,
    -- nothing of the original game is overwritten, and engineFreeModel()
    -- releases it again on resource stop.
    --
    -- Fallback for MTA builds without engineRequestModel: set this to a stock
    -- object model ID to overwrite (it is restored with engineRestoreModel /
    -- engineRestoreCOL on uninstall).  0 = no fallback, require engineRequestModel.
    stockObjectModel = 0,

    ---------------------------------------------------------------------
    -- spawning
    ---------------------------------------------------------------------
    spawnRange = 8.0,          -- metres in front of the camera for /spider
    minSpawnDistance = 2.0,    -- never spawn closer than this to the player
    groundSnap = true,         -- drop the object onto the ground below the aim point
    groundSnapTolerance = 4.0, -- only snap when the ground is within this many metres
    facePlayer = true,         -- rotate the spider so it looks at the player
    doubleSided = true,        -- render the hair/fur cards from both sides
    spawnLimit = 8,            -- remove the oldest spider above this count

    ---------------------------------------------------------------------
    -- messaging
    ---------------------------------------------------------------------
    -- "en"   English only
    -- "ar"   Arabic only
    -- "both" English and Arabic on separate lines
    -- (the GTA chat font has no Arabic glyphs on some clients - English is the
    --  safe default; use dxDrawText with an Arabic TTF if you need Arabic only)
    language = "both",
    chatColor = { 255, 205, 130 },
    debugOutput = true,        -- also print to the client console (F8)
}
