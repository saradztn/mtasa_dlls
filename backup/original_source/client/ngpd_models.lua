--[[
  NextGenPoliceDepartment - client model loader.

  * Model IDs come from engineRequestModel("object") on THIS client; they are never sent to the server
    or assumed to match other clients.  Door leaves are server objects (placeholder 1337) carrying
    element data "ngpd.model"; each client maps that name to its own ID with setElementModel.
  * Load order per model: shared TXD (one per quality tier) -> engineImportTXD -> COL -> DFF.
    One TXD imported into every model shares rasters (no per-model VRAM duplication).
  * Loading is spread over frames (a few models per tick) to avoid a long freeze.
  * Everything is released on resource stop: objects destroyed, engineFreeModel, TXD/COL/DFF destroyed.
  * HIGH tier files are marked download="false" in meta.xml and fetched with downloadFile on demand;
    any failure falls back to MEDIUM.
]]

NGPD.models = { ids = {}, objects = {}, assets = {}, loaded = false, loading = false, origin = nil }
local M = NGPD.models
local PER_TICK = 6

------------------------------------------------------------------ helpers
local function warn(msg) outputDebugString("[NGPD] " .. msg, 2) end

local function placeStatic(obj, rec)
    local x, y, z = NGPD.toWorld(rec.pos[1], rec.pos[2], rec.pos[3])
    setElementPosition(obj, x, y, z)
    setElementRotation(obj, 0, 0, NGPD.toWorldRot(0))
end

local function leafInterior(name)
    return not (name:find("gate_") or name:find("barrier_") or name:find("glass_") or name:find("exit_") or name:find("tilt_"))
end

function M.applyLeaf(obj)
    if not isElement(obj) or getElementType(obj) ~= "object" then return end
    local name = getElementData(obj, "ngpd.model")
    if not name then return end
    local id = M.ids[name]
    if not id then return end
    if getElementModel(obj) ~= id then setElementModel(obj, id) end
    setObjectBreakable(obj, false)
    if NGPD.shaders and NGPD.shaders.applyToElement then
        NGPD.shaders.applyToElement(obj, name, leafInterior(name))
    end
end

local function sweepLeaves()
    for _, obj in ipairs(getElementsByType("object", resourceRoot)) do
        if getElementData(obj, "ngpd.model") then M.applyLeaf(obj) end
    end
end

------------------------------------------------------------------ loading
local function loadOne(rec, txd)
    local id = engineRequestModel("object")
    if not id then return nil, "engineRequestModel failed (out of IDs?)" end
    local a = { id = id }
    if not engineImportTXD(txd, id) then warn("engineImportTXD failed for " .. rec.name) end
    if rec.col then
        a.col = engineLoadCOL(rec.col)
        if not a.col or not engineReplaceCOL(a.col, id) then warn("COL failed for " .. rec.name) end
    end
    a.dff = engineLoadDFF(rec.dff)
    if not a.dff or not engineReplaceModel(a.dff, id, rec.alpha and true or false) then
        engineFreeModel(id)
        if a.col and isElement(a.col) then destroyElement(a.col) end
        if a.dff and isElement(a.dff) then destroyElement(a.dff) end
        return nil, "DFF failed for " .. rec.name
    end
    local scale = NGPD.quality.profile().drawDistanceScale or 1
    engineSetModelLODDistance(id, math.min(300, (rec.lod or 150) * scale))
    return a
end

local function finishLoad()
    local profile = NGPD.quality.profile()
    for _, rec in ipairs(NGPD_DATA.models) do
        local id = M.ids[rec.name]
        if id then
            local obj = createObject(id, 0, 0, 0)
            if obj then
                placeStatic(obj, rec)
                setElementInterior(obj, NGPD.models.int or 0)
                setElementDimension(obj, NGPD.models.dim or 0)
                setObjectBreakable(obj, false)
                setElementFrozen(obj, true)
                M.objects[#M.objects + 1] = { obj = obj, rec = rec }
            end
        end
    end
    if profile.shaders and NGPD.shaders then
        NGPD.shaders.enable(profile)
        for _, o in ipairs(M.objects) do NGPD.shaders.applyToElement(o.obj, o.rec.name, o.rec.interior) end
    end
    sweepLeaves()
    if NGPD.lighting then NGPD.lighting.build(profile) end
    M.loaded, M.loading = true, false
    outputDebugString(string.format("[NGPD] loaded %d models (%s), %d static objects", #NGPD_DATA.models + #NGPD_DATA.leaves,
        NGPD.quality.name, #M.objects))
end

local function startLoad(tier)
    local path = NGPD_DATA.txd[tier]
    M.txd = engineLoadTXD(path, true)
    if not M.txd then
        if tier ~= "low" then
            warn("TXD " .. path .. " failed, falling back to LOW")
            NGPD.quality.name = "low"
            return startLoad("low")
        end
        outputChatBox("[NGPD] Could not load textures - the police HQ is unavailable.", 255, 80, 80)
        M.loading = false
        return
    end
    local queue = {}
    for _, r in ipairs(NGPD_DATA.models) do queue[#queue + 1] = r end
    for _, r in ipairs(NGPD_DATA.leaves) do queue[#queue + 1] = r end
    local i = 0
    M.loadTimer = setTimer(function()
        for _ = 1, PER_TICK do
            i = i + 1
            local rec = queue[i]
            if not rec then
                if isTimer(M.loadTimer) then killTimer(M.loadTimer) end
                M.loadTimer = nil
                finishLoad()
                return
            end
            local a, err = loadOne(rec, M.txd)
            if a then
                M.ids[rec.name] = a.id
                M.assets[#M.assets + 1] = a
            else
                warn(err)
            end
        end
    end, 50, 0)
end

-- files marked download="false" (HIGH tier) are fetched only when needed
local function highTierFiles()
    local list = { NGPD_DATA.txd.high }
    for _, t in pairs(NGPD_MATERIALS.textures) do
        -- materials <=512 px share one file between HIGH and MEDIUM; that file is a normal download, so it
        -- is not requested again (downloadFile is documented for download="false" files only)
        local h, m = t.maps.high, t.maps.medium
        if h then
            if not (m and m.normal == h.normal) then list[#list + 1] = h.normal end
            if not (m and m.surface == h.surface) then list[#list + 1] = h.surface end
        end
    end
    return list
end

-- downloadFile may fire onClientFileDownloadComplete synchronously (file already cached and valid -
-- "the event will still run"), i.e. before downloadFile even returns.  Completions are therefore
-- recorded per file name and only evaluated after all requests have been queued.
local pending = nil

local function finishPending()
    local p = pending
    if not p or p.queuing then return end
    local missing = false
    for f in pairs(p.requested) do
        if not p.completed[f] then missing = true break end
    end
    -- name match, or (if the event reports names in another form) at least as many unique completions
    if missing and p.nCompleted < p.nRequested then return end
    pending = nil
    if isTimer(p.timer) then killTimer(p.timer) end
    p.cb(p.ok)
end

local function ensureFiles(onDone)
    if NGPD.quality.name ~= "high" then return onDone(true) end
    if pending then return end                      -- a request round is already running
    pending = { requested = {}, completed = {}, nRequested = 0, nCompleted = 0, ok = true, cb = onDone, queuing = true }
    local p, n = pending, 0
    for _, f in ipairs(highTierFiles()) do
        if downloadFile(f) then p.requested[f] = true; n = n + 1 end
    end
    p.nRequested = n
    p.queuing = false
    local left = 0
    for f in pairs(p.requested) do if not p.completed[f] then left = left + 1 end end
    if left > 0 then
        outputChatBox("[NGPD] Downloading HIGH quality textures (" .. left .. " of " .. n .. " files)...", 150, 200, 255)
        -- safety net: never wait forever for a download that does not report back
        p.timer = setTimer(function()
            if pending == p then
                warn("HIGH download timed out")
                p.ok = false
                pending = nil
                p.cb(false)
            end
        end, 180000, 1)
    end
    finishPending()
end

addEventHandler("onClientFileDownloadComplete", resourceRoot, function(file, success)
    local p = pending
    if not p then return end
    file = tostring(file):gsub("\\", "/")
    if not p.completed[file] then p.completed[file] = true; p.nCompleted = p.nCompleted + 1 end
    if not success then p.ok = false; warn("download failed: " .. file) end
    finishPending()
end)

function M.load()
    if M.loading or M.loaded then return end
    M.loading = true
    if not NGPD.quality.name then NGPD.quality.init() end   -- later loads keep the in-session choice
    ensureFiles(function(ok)
        if not ok then
            outputChatBox("[NGPD] HIGH quality download failed - using MEDIUM.", 255, 200, 80)
            NGPD.quality.name = "medium"
        end
        startLoad(NGPD.quality.profile().txd)
    end)
end

function M.unload()
    if isTimer(M.loadTimer) then killTimer(M.loadTimer) end
    M.loadTimer = nil
    if NGPD.lighting then NGPD.lighting.clear() end
    if NGPD.shaders then NGPD.shaders.disable() end
    for _, o in ipairs(M.objects) do if isElement(o.obj) then destroyElement(o.obj) end end
    M.objects = {}
    -- door leaves back to the placeholder before their model IDs are freed
    for _, obj in ipairs(getElementsByType("object", resourceRoot)) do
        if getElementData(obj, "ngpd.model") then setElementModel(obj, 1337) end
    end
    for _, a in ipairs(M.assets) do
        engineFreeModel(a.id)
        if a.dff and isElement(a.dff) then destroyElement(a.dff) end
        if a.col and isElement(a.col) then destroyElement(a.col) end
    end
    M.assets, M.ids = {}, {}
    if M.txd and isElement(M.txd) then destroyElement(M.txd) end
    M.txd = nil
    M.loaded, M.loading = false, false
end

function M.reload()
    M.unload()
    M.load()
end

------------------------------------------------------------------ server sync
addEvent("ngpd:init", true)
addEventHandler("ngpd:init", resourceRoot, function(x, y, z, rz, int, dim)
    NGPD.setOrigin(x, y, z, rz)
    M.int, M.dim = int or 0, dim or 0
    if M.loaded then
        for _, o in ipairs(M.objects) do
            if isElement(o.obj) then placeStatic(o.obj, o.rec); setElementInterior(o.obj, M.int); setElementDimension(o.obj, M.dim) end
        end
        sweepLeaves()
        if NGPD.lighting then NGPD.lighting.build(NGPD.quality.profile()) end
    else
        M.load()
    end
end)

-- door leaves created/recreated after our load (relocation) or streamed in later
addEventHandler("onClientElementStreamIn", resourceRoot, function()
    if M.loaded and getElementType(source) == "object" and getElementData(source, "ngpd.model") then M.applyLeaf(source) end
end)
addEventHandler("onClientElementDataChange", resourceRoot, function(key)
    if key == "ngpd.model" and M.loaded then M.applyLeaf(source) end
end)

addEventHandler("onClientResourceStart", resourceRoot, function()
    triggerServerEvent("ngpd:ready", resourceRoot)
end)

addEventHandler("onClientResourceStop", resourceRoot, function()
    M.unload()
end)
