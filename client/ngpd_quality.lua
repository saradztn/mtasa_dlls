--[[
  NextGenPoliceDepartment - Client Quality & Performance Presets
  Supported Presets:
    * performance  (or low)         : 256 px TXD, lightweight shaders, maximum FPS
    * balanced     (or medium)      : 512 px TXD + 512 px DXT5 maps, 95 m shader distance
    * high         (High Quality)   : 1024 px TXD + 1024 px DXT5nm maps, 165 m shader distance, 40 coronas
    * ultra        (Ultra Cinema)   : 1024 px TXD + 1024 px maps, 260 m shader distance, full Golden-Hour glare
    * upscaling_4k (4K Upscaling)   : Ultra PBR + 2-Pass AMD FSR 1.0 (EASU+RCAS) Spatial 4K Upscaler for RX 580 2048SP
  Persisted client-side in @ngpd_settings.xml.
]]

NGPD.quality = { name = nil }
local FILE = "@ngpd_settings.xml"

local ALIASES = {
    med = "medium",
    perf = "performance",
    high_quality = "high",
    highquality = "high",
    ["4k"] = "upscaling_4k",
    upscale = "upscaling_4k",
    upscaling = "upscaling_4k",
}

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
        or NGPD_CONFIG.qualityProfiles.medium
end

function NGPD.quality.init()
    local q = readSetting()
    if q and ALIASES[q] then q = ALIASES[q] end
    if not NGPD_CONFIG.qualityProfiles[q or ""] then q = NGPD_CONFIG.defaultQuality end
    local info = dxGetStatus and dxGetStatus() or {}
    if q ~= "low" and info.VideoCardPSVersion and tonumber(info.VideoCardPSVersion) and tonumber(info.VideoCardPSVersion) < 3 then
        outputChatBox("[NGPD] Your GPU reports pixel shader " .. tostring(info.VideoCardPSVersion) .. " - using LOW quality.", 255, 200, 80)
        q = "low"
    end
    NGPD.quality.name = q
    if NGPD.upscaler and NGPD.upscaler.applyFromProfile then
        NGPD.upscaler.applyFromProfile(NGPD.quality.profile())
    end
    return q
end

addCommandHandler("ngpd_quality", function(_, q)
    q = q and q:lower() or ""
    if ALIASES[q] then q = ALIASES[q] end
    if not NGPD_CONFIG.qualityProfiles[q] then
        outputChatBox("[NGPD] quality: " .. tostring(NGPD.quality.name) ..
            "  (usage: /ngpd_quality performance|balanced|high|ultra|upscaling_4k|low|medium)", 150, 200, 255)
        return
    end
    if q == NGPD.quality.name then
        outputChatBox("[NGPD] Already on " .. q:upper() .. " quality.", 150, 200, 255)
        return
    end
    writeSetting(q)
    NGPD.quality.name = q
    local prof = NGPD.quality.profile()
    outputChatBox("[NGPD] Switching to " .. (prof.label or q:upper()) .. " quality...", 150, 200, 255)
    if NGPD.upscaler and NGPD.upscaler.applyFromProfile then
        NGPD.upscaler.applyFromProfile(prof)
    end
    if NGPD.models and NGPD.models.reload then NGPD.models.reload() end
end)
