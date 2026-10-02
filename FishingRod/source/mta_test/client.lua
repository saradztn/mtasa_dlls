-- Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
-- FishingRod test resource.  UNTESTED IN-GAME (no MTA client was available when this was written);
-- every step prints its result to the debug console so problems are easy to locate.
--   /fishrod          spawn the rod in front of you (attached to your right hand)
--   /fishrod drop     place the rod as a world object next to you (to look at it / test collision)
--   /fishshader       toggle the optional normal+ORM PBR shader
--   /fishrodremove    remove everything

local MODEL_NAME = "FishingRod"
local modelId, rod, shaders, maps = nil, nil, {}, {}
local MATS = { "fr_carbon", "fr_blank_label", "fr_eva", "fr_cork", "fr_rubber", "fr_alu_dark", "fr_alu_gold",
               "fr_paint", "fr_chrome", "fr_ceramic", "fr_thread", "fr_plastic", "fr_reel_plate",
               "fr_line_wound", "fr_line" }

local function log(ok, what) outputChatBox((ok and "[FishingRod] OK: " or "[FishingRod] FAILED: ") .. what, ok and 0 or 255, ok and 255 or 80, 80) end

local function loadModel()
    if modelId then return true end
    -- 1) a free, dedicated model id (MTA >= 1.6); fall back to an unused vanilla id for older clients
    modelId = engineRequestModel and engineRequestModel("object", 1337) or 2866
    log(modelId ~= false and modelId ~= nil, "model id " .. tostring(modelId))
    if not modelId then return false end
    local txd = engineLoadTXD("FishingRod.txd")
    log(txd and true or false, "engineLoadTXD")
    local col = engineLoadCOL("FishingRod.col")
    log(col and true or false, "engineLoadCOL")
    local dff = engineLoadDFF("FishingRod.dff")
    log(dff and true or false, "engineLoadDFF")
    if not (txd and col and dff) then return false end
    log(engineImportTXD(txd, modelId), "engineImportTXD")
    log(engineReplaceCOL(col, modelId), "engineReplaceCOL")
    log(engineReplaceModel(dff, modelId), "engineReplaceModel")
    return true
end

local function spawn(attach)
    if not loadModel() then return end
    if isElement(rod) then destroyElement(rod) end
    local x, y, z = getElementPosition(localPlayer)
    rod = createObject(modelId, x, y, z + 1)
    log(isElement(rod), "createObject")
    if attach then
        -- rod pointing forward from the right hand; tweak offsets to taste (x right, y forward, z up, degrees)
        attachElementToElement(rod, localPlayer, 0.18, 0.35, 0.05, 0, 0, 0)
        setElementCollisionsEnabled(rod, false)
    else
        setElementPosition(rod, x + 1.2, y, z + 0.4)
        setElementRotation(rod, 0, 0, 0)
    end
end

local function enableShader()
    if not isElement(rod) then outputChatBox("spawn the rod first (/fishrod)") return end
    for _, n in ipairs(MATS) do
        if not shaders[n] then
            local sh = dxCreateShader("shader.fx", 0, 0, false, "object")
            if not sh then log(false, "dxCreateShader " .. n) return end
            local nm = dxCreateTexture("maps/" .. n .. "_n.dds")
            local orm = dxCreateTexture("maps/" .. n .. "_orm.dds")
            dxSetShaderValue(sh, "sNormalTex", nm)
            dxSetShaderValue(sh, "sOrmTex", orm)
            engineApplyShaderToWorldTexture(sh, n, rod)
            shaders[n] = sh
            maps[#maps + 1] = nm
            maps[#maps + 1] = orm
        end
    end
    log(true, "PBR shader applied to " .. #MATS .. " textures")
end

local function disableShader()
    for n, sh in pairs(shaders) do destroyElement(sh) shaders[n] = nil end
    for _, t in ipairs(maps) do destroyElement(t) end
    maps = {}
end

addCommandHandler("fishrod", function(_, arg) spawn(arg ~= "drop") end)
addCommandHandler("fishshader", function()
    if next(shaders) then disableShader() outputChatBox("shader off") else enableShader() end
end)
addCommandHandler("fishrodremove", function()
    disableShader()
    if isElement(rod) then destroyElement(rod) end
    if modelId then engineRestoreModel(modelId) engineFreeModel(modelId) modelId = nil end
end)
