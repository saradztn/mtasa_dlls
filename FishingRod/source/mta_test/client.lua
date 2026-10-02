-- Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
-- Replaces GTA:SA model ID 321 (weapon id 10 model "Gun_dildo1") with the FishingRod.
-- Files used: FishingRod.dff / FishingRod.txd / FishingRod.col (loaded on resource start).
--   /fishrod          spawn a world object with ID 321 next to you (to look at it / check collision)
--   /fishshader       toggle the optional normal+ORM shader (applies to the fr_* textures)
--   /fishrodremove    remove the test object and restore the original model 321
-- To hold it: server side giveWeapon(player, 10, 1, true) (weapon 10 uses model 321).
-- If the rod sits wrongly in the hand, the pivot/orientation can be shifted in model.py (origin = reel seat).

local MODEL_ID = 321
local obj
local shaders, texs = {}, {}
local MATS = { "fr_carbon", "fr_blank_label", "fr_eva", "fr_cork", "fr_rubber", "fr_alu_dark", "fr_alu_gold",
               "fr_paint", "fr_chrome", "fr_ceramic", "fr_thread", "fr_plastic", "fr_reel_plate",
               "fr_line_wound", "fr_line" }

local function report(ok, what)
    outputDebugString("[FishingRod] " .. (ok and "OK: " or "FAILED: ") .. what, ok and 3 or 1)
    return ok
end

addEventHandler("onClientResourceStart", resourceRoot, function()
    -- order matters: TXD first (imported into the model id), then COL, then DFF
    local txd = engineLoadTXD("FishingRod.txd")
    if report(txd and true or false, "engineLoadTXD") then report(engineImportTXD(txd, MODEL_ID), "engineImportTXD " .. MODEL_ID) end
    local col = engineLoadCOL("FishingRod.col")
    if report(col and true or false, "engineLoadCOL") then report(engineReplaceCOL(col, MODEL_ID), "engineReplaceCOL " .. MODEL_ID) end
    local dff = engineLoadDFF("FishingRod.dff")
    if report(dff and true or false, "engineLoadDFF") then report(engineReplaceModel(dff, MODEL_ID), "engineReplaceModel " .. MODEL_ID) end
end)

addCommandHandler("fishrod", function()
    if isElement(obj) then destroyElement(obj) end
    local x, y, z = getElementPosition(localPlayer)
    obj = createObject(MODEL_ID, x + 1.2, y, z + 0.4)
    report(isElement(obj), "createObject " .. MODEL_ID)
end)

local function shaderOn()
    for _, n in ipairs(MATS) do
        if not shaders[n] then
            local sh = dxCreateShader("shader.fx", 0, 0, false, "object,ped")
            if not report(sh and true or false, "dxCreateShader " .. n) then return end
            local nm, orm = dxCreateTexture("maps/" .. n .. "_n.dds"), dxCreateTexture("maps/" .. n .. "_orm.dds")
            dxSetShaderValue(sh, "sNormalTex", nm)
            dxSetShaderValue(sh, "sOrmTex", orm)
            engineApplyShaderToWorldTexture(sh, n)      -- no element: also affects the weapon held by a ped
            shaders[n] = sh
            texs[#texs + 1] = nm
            texs[#texs + 1] = orm
        end
    end
    report(true, "shader applied")
end
local function shaderOff()
    for n, sh in pairs(shaders) do destroyElement(sh) shaders[n] = nil end
    for _, t in ipairs(texs) do destroyElement(t) end
    texs = {}
end
addCommandHandler("fishshader", function() if next(shaders) then shaderOff() else shaderOn() end end)
addCommandHandler("fishrodremove", function()
    shaderOff()
    if isElement(obj) then destroyElement(obj) end
    engineRestoreModel(MODEL_ID)
end)
