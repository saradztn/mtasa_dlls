local AR = AdvancedRendering
AR.Debug = {}

local modeOrder = { "off", "depth", "motion", "history", "rejection", "ssao", "ssr", "resolution" }
local modeNames = {
    off = "OFF",
    depth = "DEPTH",
    motion = "CAMERA MOTION",
    history = "HISTORY",
    rejection = "TEMPORAL REJECTION",
    ssao = "SSAO APPROXIMATION",
    ssr = "SSR RAY-MARCH",
    resolution = "INTERNAL RESOLUTION"
}
local modeIndexes = {
    off = 0,
    depth = 1,
    motion = 2,
    history = 3,
    rejection = 4,
    ssao = 5,
    ssr = 6,
    resolution = 7
}

function AR.Debug.getModeIndex(mode)
    return modeIndexes[string.lower(tostring(mode or "off"))] or 0
end

function AR.Debug.setMode(mode)
    mode = string.lower(tostring(mode or "off"))
    if mode == "none" then
        mode = "off"
    end
    if modeIndexes[mode] == nil then
        AR.notify("Debug modes: off, depth, motion, history, rejection, ssao, ssr, resolution", 255, 190, 120)
        return false
    end
    AR.DebugState.mode = mode
    if mode ~= "off" then
        AR.notify("Debug view: " .. (modeNames[mode] or mode))
    else
        AR.notify("Debug view disabled.")
    end
    return true
end

function AR.Debug.nextMode()
    local current = 1
    for index, mode in ipairs(modeOrder) do
        if mode == AR.DebugState.mode then
            current = index
            break
        end
    end
    current = current % #modeOrder + 1
    AR.Debug.setMode(modeOrder[current])
end

local function drawDebugPanel()
    local stats = AR.Performance and AR.Performance.getStats() or {}
    local pipeline = AR.Pipeline and AR.Pipeline.getStats() or {}
    local width, height = guiGetScreenSize()
    local x, y = 18, 18
    local boxWidth, lineHeight = 356, 18
    local lines = {
        "ARS DEBUG  |  " .. tostring(modeNames[AR.DebugState.mode] or "OFF"),
        string.format("FPS %.1f   frame %.2f ms", stats.fps or 0, stats.frameMs or 0),
        string.format("RT %dx%d -> %dx%d (%.0f%%)", pipeline.width or 0, pipeline.height or 0, pipeline.internalWidth or 0, pipeline.internalHeight or 0, (pipeline.actualScale or 0) * 100),
        string.format("Depth %s   history %s   budget %s", stats.depthAvailable and "readable" or "unavailable", pipeline.temporalValid and "valid" or "reset", tostring(stats.budgetLevel or 0)),
        string.format("Passes %d   CPU submit ~%.2f ms", stats.activePasses or 0, stats.cpuSubmitMs or 0),
        "GPU timestamps are not exposed by MTA; frame-time is the proxy."
    }

    dxDrawRectangle(x, y, boxWidth, #lines * lineHeight + 14, tocolor(8, 12, 17, 218), false)
    dxDrawRectangle(x, y, 3, #lines * lineHeight + 14, tocolor(44, 198, 236, 255), false)
    for index, text in ipairs(lines) do
        dxDrawText(text, x + 13, y + 6 + (index - 1) * lineHeight, x + boxWidth - 8, y + 6 + index * lineHeight,
            index == 1 and tocolor(82, 214, 255, 255) or tocolor(228, 237, 243, 245),
            1, "default-bold", "left", "center", true, false, false, true)
    end
    if height < 500 then
        dxDrawText("/arsdebug off", width - 150, height - 30, width - 15, height - 10, tocolor(255, 255, 255, 210), 1, "default-bold", "right", "center")
    end
end

function AR.Debug.render()
    if not AR.Config.debugOverlay then
        return
    end
    if AR.DebugState.mode ~= "off" or AR.DebugState.showPanel then
        drawDebugPanel()
    end
end

function AR.Debug.start()
    addCommandHandler(AR.Config.debugCommand, function(_, mode)
        AR.Debug.setMode(mode or "depth")
    end)
    addCommandHandler("arsnextdebug", function()
        AR.Debug.nextMode()
    end)
    addEventHandler("onClientRender", root, AR.Debug.render)
end

function AR.Debug.stop()
    removeEventHandler("onClientRender", root, AR.Debug.render)
end
