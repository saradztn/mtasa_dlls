--[[
    spider_sa / client.lua

    Installs the Dragon_2.5 spider as a custom object model and spawns it in the
    world.  Model replacement is client side in MTA, so every player that should
    see the spider runs this resource; the server side command /spiderall
    triggers the spawn for everybody and re-sends the state to players that join.

    Commands:
        /spider                 spawn (or move) a spider at the crosshair
        /spider move            move the nearest spider to the crosshair
        /spider remove          remove every spider spawned by this client
        /spider install         install the model without spawning
        /spider uninstall       free the model slot and restore everything
        /spider info            show model / asset state
]]

local C = SpiderConfig

-----------------------------------------------------------------------------
-- small helpers
-----------------------------------------------------------------------------
local function atan2(y, x)
    if math.atan2 then return math.atan2(y, x) end
    return math.atan(y, x)                                  -- Lua 5.3+ style
end

local MESSAGES = {
    -- key                     = { english, arabic }
    prefix_ok            = { "[spider] ", "[spider] " },
    installed            = { "model installed on id %d%s", "تم تركيب النموذج على المعرف %d%s" },
    allocated_note       = { " (allocated)", " (معرّف مخصص)" },
    stock_note           = { " (stock object id - restored on uninstall)", " (معرّف عنصر أصلي - يُستعاد عند الإزالة)" },
    install_failed       = { "install failed: %s", "فشل التركيب: %s" },
    uninstalled          = { "model removed, %d object(s) destroyed", "تم إزالة النموذج وتدمير %d عنصر" },
    nothing_to_uninstall = { "nothing is installed", "لا يوجد شيء مركّب" },
    spawned              = { "spider spawned at %.1f %.1f %.1f (model %d)", "تم إنشاء العنكبوت عند %.1f %.1f %.1f (النموذج %d)" },
    spawn_failed         = { "could not create the object", "تعذّر إنشاء العنصر" },
    no_aim               = { "could not resolve the aim position", "تعذّر تحديد موضع التصويب" },
    removed_count        = { "removed %d spider(s)", "تم حذف %d عنكبوت" },
    none_present         = { "no spider spawned yet", "لا يوجد عنكبوت بعد" },
    moved                = { "moved the closest spider to the crosshair", "تم نقل أقرب عنكبوت إلى مؤشر التصويب" },
    info                 = { "model id=%s allocated=%s objects=%d assets: dff=%s col=%s txd=%s", "المعرف=%s مخصص=%s العناصر=%d الملفات: dff=%s col=%s txd=%s" },
    asset_missing        = { "missing asset file: %s", "ملف مفقود: %s" },
    need_engine_request  = { "this resource needs engineRequestModel (MTA 1.6) or a stockObjectModel in config.lua", "هذا المورد يحتاج engineRequestModel (MTA 1.6) أو stockObjectModel في config.lua" },
    bad_subcommand       = { "usage: /spider [move|remove|install|uninstall|info]", "الاستخدام: /spider [move|remove|install|uninstall|info]" },
    server_spawn         = { "a spider was placed by the server", "تم وضع عنكبوت من قبل السيرفر" },
    server_removed       = { "the server removed the spiders", "السيرفر حذف العنكبوت" },
    textures             = { "model textures: %s", "تكسترات النموذج: %s" },
}

local function phrase(key)
    local entry = MESSAGES[key]
    if not entry then return key end
    return (C.language == "ar") and entry[2] or entry[1]
end

local function say(key, ...)
    local entry = MESSAGES[key]
    local en, ar
    if entry then
        en, ar = string.format(entry[1], ...), string.format(entry[2], ...)
    else
        en, ar = tostring(key), tostring(key)
    end
    local text
    if C.language == "ar" then
        text = ar
    elseif C.language == "both" then
        text = en .. "\n" .. ar
    else
        text = en
    end
    local r, g, b = C.chatColor[1], C.chatColor[2], C.chatColor[3]
    outputChatBox("[spider] " .. text, r, g, b)
    if C.debugOutput then
        outputDebugString("[spider] " .. en)
    end
end

-- install() returns (false, reason[, detail]); give the two interesting reasons
-- their own chat messages so a missing asset names the file it wanted.
local function reportInstallError(reason, detail)
    if reason == "engineRequestModel" then
        say("need_engine_request")
    elseif reason == "asset_missing" then
        say("asset_missing", tostring(detail or "?"))
    else
        say("install_failed", tostring(reason))
    end
end

-----------------------------------------------------------------------------
-- state
-----------------------------------------------------------------------------
local objects = {}                 -- spawned spider objects (client side)
local globalSpider = nil           -- { x, y, z, rot } placed by the server
local model = {
    id = false,
    allocated = false,
    installed = false,
    textures = nil,
    peer = nil,                    -- the dff/col/txd elements currently in use
}

-----------------------------------------------------------------------------
-- model installation
-----------------------------------------------------------------------------
local function asset(name)
    if not fileExists(name) then
        return nil, string.format("missing %s", name)
    end
    return name
end

local function cleanupPeer()
    -- the DFF element is consumed by engineReplaceModel, so simply drop refs
    model.peer = nil
end

local function install()
    if model.installed then return true end

    local dff = asset(C.dffFile)
    if not dff then return false, "asset_missing", C.dffFile end
    local col = asset(C.colFile)
    if not col then return false, "asset_missing", C.colFile end
    local txd = asset(C.txdFile)
    if not txd then return false, "asset_missing", C.txdFile end

    -- pick a model slot
    local modelId, allocated = false, false
    if engineRequestModel then
        modelId = engineRequestModel("object")
        if modelId then allocated = true end
    end
    if not modelId then
        if (C.stockObjectModel or 0) > 0 then
            modelId, allocated = C.stockObjectModel, false
        else
            return false, "engineRequestModel"
        end
    end

    -- engine loading order: COL -> TXD -> DFF
    local colElement = engineLoadCOL(col)
    if not colElement then
        if allocated then engineFreeModel(modelId) end
        return false, "engineLoadCOL failed"
    end
    local txdElement = engineLoadTXD(txd, C.txdFiltering and true or false)
    if not txdElement then
        if allocated then engineFreeModel(modelId) end
        return false, "engineLoadTXD failed"
    end
    local dffElement = engineLoadDFF(dff)
    if not dffElement then
        if allocated then engineFreeModel(modelId) end
        return false, "engineLoadDFF failed"
    end

    local okCol = engineReplaceCOL(colElement, modelId)
    local okTxd = engineImportTXD(txdElement, modelId)
    local okDff = engineReplaceModel(dffElement, modelId)
    if not okDff then
        if allocated then engineFreeModel(modelId) end
        return false, "engineReplaceModel failed"
    end

    model.id = modelId
    model.allocated = allocated
    model.installed = true
    model.peer = { col = colElement, txd = txdElement, dff = okDff and false or dffElement }

    -- optional diagnostics: which textures the engine reports for this model
    model.textures = nil
    if engineGetModelTextureNames and engineGetModelNameFromID then
        local modelName = engineGetModelNameFromID(modelId)
        if modelName then
            local names = engineGetModelTextureNames(modelName)
            if type(names) == "table" and #names > 0 then
                model.textures = table.concat(names, ", ")
            end
        end
    end

    say("installed", modelId, phrase(allocated and "allocated_note" or "stock_note"))
    if C.debugOutput then
        outputDebugString(string.format("[spider] col=%s txd=%s dff=%s",
            tostring(okCol), tostring(okTxd), tostring(okDff)))
        if model.textures then outputDebugString("[spider] textures: " .. model.textures) end
    end
    return true
end

local function uninstall()
    local removed = 0
    for i = #objects, 1, -1 do
        if isElement(objects[i]) then
            destroyElement(objects[i])
            removed = removed + 1
        end
        objects[i] = nil
    end
    if not model.installed then
        return removed, false
    end
    if model.allocated and engineFreeModel then
        engineFreeModel(model.id)
    else
        if engineRestoreModel then engineRestoreModel(model.id) end
        if engineRestoreCOL then engineRestoreCOL(model.id) end
        if engineStreamingReleaseModel then engineStreamingReleaseModel(model.id) end
    end
    model.id, model.installed, model.allocated, model.textures = false, false, false, nil
    cleanupPeer()
    return removed, true
end

-----------------------------------------------------------------------------
-- spawning
-----------------------------------------------------------------------------
-- resolve the point the camera is aiming at
local function getAimPosition(range)
    local cx, cy, cz, tx, ty, tz = getCameraMatrix()
    if not cx then return nil end

    local dirX, dirY, dirZ = tx - cx, ty - cy, tz - cz

    -- if available, use the true crosshair ray for accuracy
    if getWorldFromScreenPosition then
        local w, h = guiGetScreenSize()
        if w and h then
            local wx, wy, wz = getWorldFromScreenPosition(w * 0.5, h * 0.5, range)
            if wx then
                dirX, dirY, dirZ = wx - cx, wy - cy, wz - cz
            end
        end
    end

    local len = math.sqrt(dirX * dirX + dirY * dirY + dirZ * dirZ)
    if len < 0.001 then return nil end
    dirX, dirY, dirZ = dirX / len, dirY / len, dirZ / len

    local ex, ey, ez = cx + dirX * range, cy + dirY * range, cz + dirZ * range
    local hit, hx, hy, hz = processLineOfSight(cx, cy, cz, ex, ey, ez,
        true, false, false, true)      -- buildings, vehicles, peds, objects
    if hit and hx then
        return hx, hy, hz
    end
    return ex, ey, ez
end

local function snapToGround(x, y, z)
    if not C.groundSnap then return z end
    local groundZ = getGroundPosition(x, y, z + 1.0)
    if groundZ and math.abs(groundZ - z) <= C.groundSnapTolerance then
        return groundZ + 0.02
    end
    return z
end

local function spawnAt(x, y, z)
    local ok, err, detail = install()
    if not ok then
        reportInstallError(err, detail)
        return false
    end

    -- do not spawn on top of the player
    local px, py, pz = getElementPosition(localPlayer)
    local dx, dy = x - px, y - py
    local dist = math.sqrt(dx * dx + dy * dy)
    if dist < C.minSpawnDistance then
        local scale = C.minSpawnDistance / (dist > 0.001 and dist or 0.001)
        x, y = px + dx * scale, py + dy * scale
    end

    z = snapToGround(x, y, z)

    local object = createObject(model.id, x, y, z, 0, 0, 0)
    if not object then
        say("spawn_failed")
        return false
    end

    if setElementDoubleSided then
        setElementDoubleSided(object, C.doubleSided and true or false)
    end
    setElementDimension(object, getElementDimension(localPlayer))
    setElementInterior(object, getElementInterior(localPlayer))

    if C.facePlayer then
        local fx, fy = getElementPosition(localPlayer)
        setElementRotation(object, 0, 0, -math.deg(atan2(fx - x, fy - y)))
    end

    table.insert(objects, object)
    while #objects > C.spawnLimit do
        local oldest = table.remove(objects, 1)
        if isElement(oldest) then destroyElement(oldest) end
    end

    say("spawned", x, y, z, model.id)
    return object
end

local function removeAll()
    local count = 0
    for i = #objects, 1, -1 do
        if isElement(objects[i]) then
            destroyElement(objects[i])
            count = count + 1
        end
        objects[i] = nil
    end
    say("removed_count", count)
    return count
end

local function nearestSpider()
    local px, py, pz = getElementPosition(localPlayer)
    local best, bestDist
    for _, object in ipairs(objects) do
        if isElement(object) then
            local ox, oy, oz = getElementPosition(object)
            local dx, dy, dz = ox - px, oy - py, oz - pz
            local d = dx * dx + dy * dy + dz * dz
            if not bestDist or d < bestDist then best, bestDist = object, d end
        end
    end
    return best
end

-----------------------------------------------------------------------------
-- commands
-----------------------------------------------------------------------------
local function commandSpawn()
    local x, y, z = getAimPosition(C.spawnRange)
    if not x then
        say("no_aim")
        return
    end
    spawnAt(x, y, z)
end

local function commandMove()
    local object = nearestSpider()
    if not object then
        say("none_present")
        return
    end
    local x, y, z = getAimPosition(C.spawnRange)
    if not x then
        say("no_aim")
        return
    end
    z = snapToGround(x, y, z)
    setElementPosition(object, x, y, z)
    if C.facePlayer then
        local fx, fy = getElementPosition(localPlayer)
        setElementRotation(object, 0, 0, -math.deg(atan2(fx - x, fy - y)))
    end
    say("moved")
end

-- MTA calls command handlers as (player, commandName, ...arguments)
addCommandHandler("spider", function(_, _, sub)
    sub = string.lower(tostring(sub or "spawn"))
    if sub == "" or sub == "spawn" then
        commandSpawn()
    elseif sub == "move" then
        commandMove()
    elseif sub == "remove" or sub == "clear" then
        removeAll()
    elseif sub == "install" then
        local ok, err, detail = install()
        if not ok then reportInstallError(err, detail) end
    elseif sub == "uninstall" then
        local removed, freed = uninstall()
        if freed then say("uninstalled", removed) else say("nothing_to_uninstall") end
    elseif sub == "info" then
        say("info", tostring(model.id), tostring(model.allocated), #objects,
            tostring(fileExists(C.dffFile)), tostring(fileExists(C.colFile)), tostring(fileExists(C.txdFile)))
        if model.textures then say("textures", model.textures) end
    else
        say("bad_subcommand")
    end
end, false, false)

-----------------------------------------------------------------------------
-- server driven global spider
-----------------------------------------------------------------------------
addEvent("spiderSa:spawn", true)
addEvent("spiderSa:remove", true)

addEventHandler("spiderSa:spawn", root, function(x, y, z, rot)
    if type(x) ~= "number" or type(y) ~= "number" or type(z) ~= "number" then return end
    -- small delay so this also works when the state arrives while the client
    -- resource is still starting up
    setTimer(function()
        local object = spawnAt(x, y, z)
        if not object then return end
        if type(rot) == "number" then
            setElementRotation(object, 0, 0, rot)
        end
        globalSpider = { x = x, y = y, z = z, rot = rot }
        say("server_spawn")
    end, 200, 1)
end)

addEventHandler("spiderSa:remove", root, function()
    globalSpider = nil
    removeAll()
    say("server_removed")
end)

-----------------------------------------------------------------------------
-- lifecycle
-----------------------------------------------------------------------------
addEventHandler("onClientResourceStart", resourceRoot, function()
    if C.installOnStart then
        local ok, err, detail = install()
        if not ok then reportInstallError(err, detail) end
    end
    -- ask the server whether a global spider is already placed
    if triggerServerEvent then
        triggerServerEvent("spiderSa:requestState", localPlayer)
    end
end)

addEventHandler("onClientResourceStop", resourceRoot, function()
    -- engineRequestModel side effects are NOT reverted automatically, so the
    -- model slot must be freed here
    uninstall()
end)
