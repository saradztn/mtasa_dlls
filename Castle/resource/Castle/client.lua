-- Created by: Arena.ai Agent Mode (AI) - Castle MTA:SA resource
-- ---------------------------------------------------------------------------------------------
-- client.lua - loads the castle DFF / TXD / COL and replaces three vanilla object models.
--   12853 (sw_gas01, Dillimore petrol station)  -> the castle
--   12854 (sw_gas01int)                         -> main gate leaf (arched, iron bound)
--   12855 (sw_copshop)                          -> interior door leaf
-- The original buildings (one instance each, in Dillimore) are hidden with removeWorldModel while the
-- resource runs, and restored when it stops.  Change the three ids here AND in server.lua (and in
-- build.py -> ID_* for the COL header) if you prefer other objects.
-- ---------------------------------------------------------------------------------------------
local IDS = { castle = 12853, gate = 12854, door = 12855 }
local FILES = {
    castle = { dff = "files/Castle.dff",     col = "files/Castle.col" },
    gate   = { dff = "files/CastleGate.dff", col = "files/CastleGate.col" },
    door   = { dff = "files/CastleDoor.dff", col = "files/CastleDoor.col" },
}
local TXD_FILE = "files/Castle.txd"
local LOD_DISTANCE = 900.0          -- the castle is huge: keep it drawn from far away

local loaded = {}                   -- elements kept so that they can be destroyed on stop
local hidden = {}                   -- world models that were removed

local function fail(msg)
    outputChatBox("[Castle] " .. msg, 255, 80, 80)
    outputDebugString("[Castle] " .. msg, 1)
end

local function replaceOne(kind, txd)
    local id, f = IDS[kind], FILES[kind]
    local col = engineLoadCOL(f.col)
    if not col then return fail("could not load " .. f.col) end
    local dff = engineLoadDFF(f.dff)
    if not dff then return fail("could not load " .. f.dff) end
    loaded[#loaded + 1] = col
    loaded[#loaded + 1] = dff
    if not engineReplaceCOL(col, id) then return fail("engineReplaceCOL failed for " .. id) end
    if not engineImportTXD(txd, id) then return fail("engineImportTXD failed for " .. id) end
    if not engineReplaceModel(dff, id) then return fail("engineReplaceModel failed for " .. id) end
    engineSetModelLODDistance(id, LOD_DISTANCE)
    return true
end

addEventHandler("onClientResourceStart", resourceRoot, function()
    local txd = engineLoadTXD(TXD_FILE)
    if not txd then return fail("could not load " .. TXD_FILE) end
    loaded[#loaded + 1] = txd
    -- hide the original map objects that use these ids (one instance each, around Dillimore)
    for _, id in pairs(IDS) do
        if removeWorldModel(id, 6000, 0, 0, 0) then hidden[#hidden + 1] = id end
    end
    local okAll = true
    for _, kind in ipairs({ "castle", "gate", "door" }) do
        if not replaceOne(kind, txd) then okAll = false end
    end
    if okAll then
        outputChatBox("[Castle] models loaded. Type /showx to build the castle in front of you, /hidex to remove it.", 120, 220, 120)
    end
end)

addEventHandler("onClientResourceStop", resourceRoot, function()
    for _, id in ipairs(hidden) do restoreWorldModel(id, 6000, 0, 0, 0) end
    for _, id in pairs(IDS) do
        engineRestoreModel(id)
        engineResetModelLODDistance(id)
    end
    for _, e in ipairs(loaded) do
        if isElement(e) then destroyElement(e) end
    end
end)
