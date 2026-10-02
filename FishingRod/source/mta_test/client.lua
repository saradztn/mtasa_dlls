-- Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
-- FULLY AUTOMATIC: when the resource starts, model ID 321 (weapon 10) is replaced by the FishingRod
-- (FishingRod.txd -> FishingRod.col -> FishingRod.dff).  No commands.  When the resource stops MTA restores
-- the original model by itself.  The rod is already rotated +90 deg about Z inside the DFF/COL.
-- Results are written to the debug console (/debugscript 3).

local MODEL_ID = 321
local USE_SHADER = false     -- optional normal/ORM shader (shader.fx); off by default = the look you tested

local function report(ok, what)
    outputDebugString("[FishingRod] " .. (ok and "OK: " or "FAILED: ") .. what, ok and 3 or 1)
    return ok
end

local function replaceModel()
    local txd = engineLoadTXD("FishingRod.txd")
    if report(txd and true or false, "engineLoadTXD") then report(engineImportTXD(txd, MODEL_ID), "engineImportTXD " .. MODEL_ID) end
    local col = engineLoadCOL("FishingRod.col")
    if report(col and true or false, "engineLoadCOL") then report(engineReplaceCOL(col, MODEL_ID), "engineReplaceCOL " .. MODEL_ID) end
    local dff = engineLoadDFF("FishingRod.dff")
    if report(dff and true or false, "engineLoadDFF") then report(engineReplaceModel(dff, MODEL_ID), "engineReplaceModel " .. MODEL_ID) end
end

local MATS = { "fr_carbon", "fr_blank_label", "fr_eva", "fr_cork", "fr_rubber", "fr_alu_dark", "fr_alu_gold",
               "fr_paint", "fr_chrome", "fr_ceramic", "fr_thread", "fr_plastic", "fr_reel_plate",
               "fr_line_wound", "fr_line" }

local function applyShader()
    for _, n in ipairs(MATS) do
        local sh = dxCreateShader("shader.fx", 0, 0, false, "object,ped")
        if not report(sh and true or false, "dxCreateShader " .. n) then return end
        dxSetShaderValue(sh, "sNormalTex", dxCreateTexture("maps/" .. n .. "_n.dds"))
        dxSetShaderValue(sh, "sOrmTex", dxCreateTexture("maps/" .. n .. "_orm.dds"))
        engineApplyShaderToWorldTexture(sh, n)
    end
    report(true, "PBR shader applied")
end

addEventHandler("onClientResourceStart", resourceRoot, function()
    replaceModel()
    if USE_SHADER then applyShader() end
end)
