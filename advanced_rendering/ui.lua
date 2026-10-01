local AR = AdvancedRendering
AR.UI = {
    open = false,
    scale = 1,
    bounds = {},
    previousCursor = false,
    started = false,
    profileOrder = { "ULTRA", "HIGH", "MEDIUM", "LOW", "COMPATIBILITY" },
    scaleOrder = { 1.00, 0.85, 0.75, 0.67, 0.50 },
    featureOrder = {
        { name = "enabled", label = "Rendering pipeline", kind = "master" },
        { name = "quality", label = "Quality profile", kind = "quality" },
        { name = "resolutionScale", label = "Post-process resolution", kind = "scale" },
        { name = "dynamicResolution", label = "Dynamic resolution", kind = "state" },
        { name = "temporal", label = "Temporal reconstruction", kind = "feature" },
        { name = "reconstruction", label = "Depth-guided detail reconstruction", kind = "feature" },
        { name = "superResolution", label = "Catmull-Rom reconstruction", kind = "feature" },
        { name = "taa", label = "Hybrid edge AA", kind = "feature" },
        { name = "ssao", label = "Depth SSAO approximation", kind = "feature" },
        { name = "ssr", label = "Screen-space reflections", kind = "feature" },
        { name = "shadowEnhancement", label = "Contact shadow approximation", kind = "feature" },
        { name = "vehicleResponse", label = "Vehicle paint response", kind = "feature" },
        { name = "materialEnhancement", label = "Named world materials", kind = "feature" },
        { name = "sharpen", label = "Depth-aware detail recovery", kind = "feature" },
        { name = "toneMapping", label = "LDR filmic highlight roll-off", kind = "feature" },
        { name = "autoExposure", label = "Auto exposure (LDR estimate)", kind = "feature" },
        { name = "colorManagement", label = "Color management", kind = "feature" }
    }
}

local function color(r, g, b, a)
    return tocolor(r, g, b, a or 255)
end

local function stateValue(item)
    if item.kind == "master" then
        return AR.State.enabled
    elseif item.kind == "quality" then
        return AR.State.quality
    elseif item.kind == "scale" then
        return string.format("%d%%", math.floor(((AR.Pipeline.ready and AR.Pipeline.actualScale) or AR.State.resolutionScale) * 100 + 0.5))
    elseif item.kind == "state" then
        return AR.State.dynamicResolution
    end
    return AR.State.features[item.name] == true
end

local function formatValue(item)
    local value = stateValue(item)
    if item.kind == "quality" or item.kind == "scale" then
        return tostring(value)
    end
    return value and "ON" or "OFF"
end

local function drawButton(x, y, w, h, title, selected, hover)
    local fill = selected and color(24, 133, 166, 230) or (hover and color(49, 67, 80, 245) or color(27, 36, 45, 235))
    dxDrawRectangle(x, y, w, h, fill, false)
    dxDrawRectangle(x, y, w, 1, selected and color(79, 219, 255) or color(61, 78, 92), false)
    dxDrawText(title, x + 5, y, x + w - 5, y + h, color(236, 243, 247), 0.86, "default-bold", "center", "center", true, false, false, true)
end

local function layout()
    local screenW, screenH = guiGetScreenSize()
    local scale = math.min(1.0, screenH / 820)
    scale = math.max(0.72, scale)
    local width = 720 * scale
    local height = 670 * scale
    local x = math.max(12, (screenW - width) * 0.5)
    local y = math.max(12, (screenH - height) * 0.5)
    return x, y, width, height, scale, screenW, screenH
end

local function drawPanel()
    local x, y, width, height, scale, sw, sh = layout()
    AR.UI.scale = scale
    AR.UI.bounds = {}
    dxDrawRectangle(x, y, width, height, color(10, 15, 21, 245), false)
    dxDrawRectangle(x, y, width, 52 * scale, color(17, 27, 36, 255), false)
    dxDrawRectangle(x, y + 50 * scale, width, 2 * scale, color(50, 198, 235), false)

    dxDrawText("ADVANCED RENDERING SYSTEM", x + 22 * scale, y + 8 * scale, x + width - 115 * scale, y + 31 * scale,
        color(235, 247, 251), 1.05 * scale, "default-bold", "left", "center", true, false, false, true)
    dxDrawText("MTA-native post-process pipeline  •  F10 / /ars", x + 22 * scale, y + 29 * scale, x + width - 115 * scale, y + 47 * scale,
        color(135, 169, 187), 0.78 * scale, "default", "left", "center", true, false, false, true)
    drawButton(x + width - 82 * scale, y + 10 * scale, 62 * scale, 30 * scale, "CLOSE", false, false)
    AR.UI.bounds.close = { x + width - 82 * scale, y + 10 * scale, 62 * scale, 30 * scale }

    local presetNames = { "ULTRA QUALITY", "HIGH", "CINEMATIC", "REALISTIC", "BALANCED", "PERFORMANCE" }
    local padding = 18 * scale
    local gap = 7 * scale
    local presetY = y + 68 * scale
    local presetW = (width - padding * 2 - gap * (#presetNames - 1)) / #presetNames
    dxDrawText("PRESETS", x + padding, presetY - 15 * scale, x + width - padding, presetY, color(116, 151, 168), 0.72 * scale, "default-bold", "left", "center")
    for index, name in ipairs(presetNames) do
        local bx = x + padding + (index - 1) * (presetW + gap)
        local selected = string.upper(AR.State.preset or "") == name
        drawButton(bx, presetY, presetW, 34 * scale, name, selected, false)
        AR.UI.bounds["preset:" .. name] = { bx, presetY, presetW, 34 * scale }
    end

    local stats = AR.Performance.getStats()
    local pipeline = AR.Pipeline.getStats()
    local infoY = presetY + 48 * scale
    dxDrawRectangle(x + padding, infoY, width - padding * 2, 49 * scale, color(18, 27, 34, 220), false)
    dxDrawText(string.format("%s  |  %.1f FPS  |  %.2f ms/frame  |  %d%% post scale", tostring(AR.State.quality), stats.fps or 0, stats.frameMs or 0, math.floor((pipeline.actualScale or 0) * 100 + 0.5)),
        x + padding + 12 * scale, infoY + 5 * scale, x + width - padding - 8 * scale, infoY + 24 * scale,
        color(220, 233, 239), 0.84 * scale, "default-bold", "left", "center", true, false, false, true)
    local depthText = stats.depthAvailable and "readable" or "unavailable (depth-dependent effects are bypassed)"
    dxDrawText("Depth: " .. depthText .. "   •   GPU timestamps: unavailable; DRS uses frame-time/FPS feedback",
        x + padding + 12 * scale, infoY + 25 * scale, x + width - padding - 8 * scale, infoY + 44 * scale,
        color(139, 164, 177), 0.72 * scale, "default", "left", "center", true, false, false, true)

    local listY = infoY + 62 * scale
    local rowH = 39 * scale
    local colGap = 12 * scale
    local colW = (width - padding * 2 - colGap) / 2
    local leftItems, rightItems = {}, {}
    for index, item in ipairs(AR.UI.featureOrder) do
        if index <= 8 then
            leftItems[#leftItems + 1] = item
        else
            rightItems[#rightItems + 1] = item
        end
    end

    local function drawColumn(items, columnX, columnName)
        for index, item in ipairs(items) do
            local rowY = listY + (index - 1) * rowH
            local isHovered = false
            local cursorX, cursorY = getCursorPosition()
            if cursorX and cursorY then
                cursorX, cursorY = cursorX * sw, cursorY * sh
                isHovered = cursorX >= columnX and cursorX <= columnX + colW and cursorY >= rowY and cursorY <= rowY + rowH - 3 * scale
            end
            local value = stateValue(item)
            local isOn = value == true or (item.kind == "quality" and value == "ULTRA")
            dxDrawRectangle(columnX, rowY, colW, rowH - 3 * scale, isHovered and color(27, 42, 52, 245) or color(17, 25, 32, 224), false)
            dxDrawText(item.label, columnX + 10 * scale, rowY, columnX + colW * 0.68, rowY + rowH - 3 * scale,
                color(207, 221, 228), 0.79 * scale, "default", "left", "center", true, false, false, true)
            local indicatorW = 76 * scale
            local indicatorX = columnX + colW - indicatorW - 7 * scale
            local indicatorColor = isOn and color(23, 119, 137, 230) or color(45, 52, 58, 230)
            dxDrawRectangle(indicatorX, rowY + 6 * scale, indicatorW, rowH - 15 * scale, indicatorColor, false)
            dxDrawText(formatValue(item), indicatorX + 2 * scale, rowY + 6 * scale, indicatorX + indicatorW - 2 * scale, rowY + rowH - 9 * scale,
                color(240, 247, 250), 0.75 * scale, "default-bold", "center", "center", true, false, false, true)
            AR.UI.bounds["control:" .. item.name] = { columnX, rowY, colW, rowH - 3 * scale, item }
        end
    end
    drawColumn(leftItems, x + padding, "left")
    drawColumn(rightItems, x + padding + colW + colGap, "right")

    local footerY = y + height - 42 * scale
    dxDrawText("/ars on|off|preset <name>|quality <ultra|high|medium|low|compatibility>  •  /arsdebug <mode>",
        x + padding, footerY, x + width - padding, footerY + 17 * scale, color(118, 147, 162), 0.68 * scale, "default", "left", "center", true, false, false, true)
    dxDrawText("Not an engine render-target replacement: internal scale affects post-processing, not GTA scene rasterization.",
        x + padding, footerY + 17 * scale, x + width - padding, footerY + 34 * scale, color(104, 132, 146), 0.66 * scale, "default", "left", "center", true, false, false, true)
end

local function toggleFeature(name)
    local nextValue = not AR.State.features[name]
    AR.Pipeline.setFeature(name, nextValue)
    AR.notify(name .. " " .. (nextValue and "enabled" or "disabled"))
end

local function cycleQuality()
    local current = string.upper(tostring(AR.State.quality or "HIGH"))
    local index = 1
    for i, name in ipairs(AR.UI.profileOrder) do
        if name == current then index = i break end
    end
    index = index % #AR.UI.profileOrder + 1
    AR.Performance.setQuality(AR.UI.profileOrder[index])
end

local function cycleScale()
    local current = (AR.Pipeline.ready and AR.Pipeline.actualScale) or AR.State.resolutionScale or 0.75
    local index = 1
    for i, value in ipairs(AR.UI.scaleOrder) do
        if math.abs(value - current) < 0.025 then index = i break end
    end
    index = index % #AR.UI.scaleOrder + 1
    AR.Performance.setResolutionScale(AR.UI.scaleOrder[index])
end

local function hitTest(x, y, rect)
    return rect and x >= rect[1] and x <= rect[1] + rect[3] and y >= rect[2] and y <= rect[2] + rect[4]
end

function AR.UI.handleClick(button, state, absoluteX, absoluteY)
    if not AR.UI.open or button ~= "left" or state ~= "down" then
        return
    end
    if hitTest(absoluteX, absoluteY, AR.UI.bounds.close) then
        AR.UI.setOpen(false)
        cancelEvent()
        return
    end

    for key, rect in pairs(AR.UI.bounds) do
        if key:sub(1, 7) == "preset:" and hitTest(absoluteX, absoluteY, rect) then
            local name = key:sub(8)
            AR.applyPreset(name)
            cancelEvent()
            return
        end
    end

    for key, rect in pairs(AR.UI.bounds) do
        if key:sub(1, 8) == "control:" and hitTest(absoluteX, absoluteY, rect) then
            local name = key:sub(9)
            local item = rect[5]
            if item.kind == "master" then
                AR.Pipeline.setEnabled(not AR.State.enabled)
            elseif item.kind == "quality" then
                cycleQuality()
            elseif item.kind == "scale" then
                cycleScale()
            elseif item.kind == "state" then
                AR.State.dynamicResolution = not AR.State.dynamicResolution
                if not AR.State.dynamicResolution then
                    AR.Performance.budgetLevel = 0
                end
            else
                toggleFeature(name)
            end
            cancelEvent()
            return
        end
    end

    local x0, y0, width, height = layout()
    if absoluteX < x0 or absoluteX > x0 + width or absoluteY < y0 or absoluteY > y0 + height then
        AR.UI.setOpen(false)
    end
end

function AR.UI.render()
    if AR.UI.open then
        drawPanel()
    end
end

function AR.UI.isOpen()
    return AR.UI.open == true
end

function AR.UI.setOpen(open)
    open = open == true
    if AR.UI.open == open then
        return
    end
    AR.UI.open = open
    if open then
        AR.UI.previousCursor = isCursorShowing()
        showCursor(true)
        guiSetInputEnabled(true)
    else
        guiSetInputEnabled(false)
        if not AR.UI.previousCursor then
            showCursor(false)
        end
        AR.UI.previousCursor = false
    end
end

function AR.UI.toggle()
    AR.UI.setOpen(not AR.UI.open)
end

function AR.UI.start()
    if AR.UI.started then
        return
    end
    AR.UI.started = true
    bindKey(AR.Config.uiKey, "down", AR.UI.toggle)
    addCommandHandler("arsmenu", AR.UI.toggle)
    addEventHandler("onClientClick", root, AR.UI.handleClick)
    addEventHandler("onClientRender", root, AR.UI.render)
end

function AR.UI.stop()
    if AR.UI.open then
        AR.UI.setOpen(false)
    end
    if AR.UI.started then
        unbindKey(AR.Config.uiKey, "down", AR.UI.toggle)
        removeEventHandler("onClientClick", root, AR.UI.handleClick)
        removeEventHandler("onClientRender", root, AR.UI.render)
    end
    AR.UI.started = false
end
