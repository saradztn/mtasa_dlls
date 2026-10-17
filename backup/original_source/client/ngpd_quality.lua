--[[
  NextGenPoliceDepartment - client quality profiles (LOW / MEDIUM / HIGH).
  What each level really changes (see NGPD_CONFIG.qualityProfiles):
    LOW    256 px TXD, no HLSL shaders, no wet rendering, 0 night coronas, shorter model draw distance
    MEDIUM 512 px TXD, shaders with <=512 px normal/surface maps, shader max distance 60 m, 12 coronas
    HIGH   1024 px TXD + full-res maps (downloaded on demand), shader distance 140 m, 40 coronas
  The choice is stored client-side in @ngpd_settings.xml (private to this resource).
]]

NGPD.quality = { name = nil }
local FILE = "@ngpd_settings.xml"

local function readSetting()
    local xml = xmlLoadFile(FILE)
    if not xml then return nil end
    local q = xmlNodeGetAttribute(xml, "quality")
    xmlUnloadFile(xml)
    return q
end

local function writeSetting(q)
    local xml = xmlLoadFile(FILE) or xmlCreateFile(FILE, "ngpd")
    if not xml then return end
    xmlNodeSetAttribute(xml, "quality", q)
    xmlSaveFile(xml)
    xmlUnloadFile(xml)
end

function NGPD.quality.profile()
    return NGPD_CONFIG.qualityProfiles[NGPD.quality.name or NGPD_CONFIG.defaultQuality]
end

function NGPD.quality.init()
    local q = readSetting()
    if not NGPD_CONFIG.qualityProfiles[q or ""] then q = NGPD_CONFIG.defaultQuality end
    -- very old GPUs: no pixel shader 3.0 -> LOW avoids creating shaders that would only hit the fallback
    local info = dxGetStatus and dxGetStatus() or {}
    if q ~= "low" and info.VideoCardPSVersion and tonumber(info.VideoCardPSVersion) and tonumber(info.VideoCardPSVersion) < 3 then
        outputChatBox("[NGPD] Your GPU reports pixel shader " .. tostring(info.VideoCardPSVersion) .. " - using LOW quality.", 255, 200, 80)
        q = "low"
    end
    NGPD.quality.name = q
    return q
end

addCommandHandler("ngpd_quality", function(_, q)
    q = q and q:lower() or ""
    if q == "med" then q = "medium" end
    if not NGPD_CONFIG.qualityProfiles[q] then
        outputChatBox("[NGPD] quality: " .. tostring(NGPD.quality.name) .. "  (usage: /ngpd_quality low|medium|high)", 150, 200, 255)
        return
    end
    if q == NGPD.quality.name then return end
    writeSetting(q)
    NGPD.quality.name = q
    outputChatBox("[NGPD] Switching to " .. q:upper() .. " quality...", 150, 200, 255)
    if NGPD.models and NGPD.models.reload then NGPD.models.reload() end
end)
