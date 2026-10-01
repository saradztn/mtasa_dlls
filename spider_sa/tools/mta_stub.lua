--[[
    spider_sa / tools/mta_stub.lua

    Minimal client-side MTA:SA API mock used by tools/smoke_test.js so the real
    resource Lua can be executed offline (fengari / Lua 5.3).  Every function
    records its calls in the global `_calls` table and returns plausible values,
    which lets the test assert on the exact engine call sequence.  This is a
    development aid only - it is never loaded by the game.
]]

_calls = { order = {} }
_state = {
    installed = nil,        -- model id handed out by engineRequestModel
    freed = {},
    objects = {},
    nextObject = 1,
    handlers = {},
    commands = {},
    chat = {},
    debug = {},
    events = {},
}

local function record(name, ...)
    table.insert(_calls.order, { name = name, args = { ... } })
end
_calls.record = record

-----------------------------------------------------------------------------
-- output
-----------------------------------------------------------------------------
function outputChatBox(text, r, g, b)
    table.insert(_state.chat, tostring(text))
    record("outputChatBox", text, r, g, b)
    return true
end

function outputDebugString(text)
    table.insert(_state.debug, tostring(text))
    record("outputDebugString", text)
    return true
end

-----------------------------------------------------------------------------
-- clientside files
-----------------------------------------------------------------------------
function fileExists(path)
    -- the test preloads this table with the resource files that really exist
    return _files and _files[tostring(path)] == true
end

-----------------------------------------------------------------------------
-- engine model API
-----------------------------------------------------------------------------
function engineRequestModel(elementType, parentId)
    record("engineRequestModel", elementType, parentId)
    if _state.installed then return false end          -- no free slot in the fake
    _state.installed = 20000
    return 20000
end

function engineFreeModel(modelId)
    record("engineFreeModel", modelId)
    _state.installed = nil
    table.insert(_state.freed, modelId)
    return true
end

function engineLoadCOL(path)
    record("engineLoadCOL", path)
    return { element = "col", path = path }
end

function engineLoadTXD(path, filteringEnabled)
    record("engineLoadTXD", path, filteringEnabled)
    return { element = "txd", path = path, filtering = filteringEnabled }
end

function engineLoadDFF(path, modelId)
    record("engineLoadDFF", path, modelId)
    return { element = "dff", path = path }
end

function engineReplaceCOL(col, modelId)
    record("engineReplaceCOL", col and col.path, modelId)
    return true
end

function engineImportTXD(txd, modelId)
    record("engineImportTXD", txd and txd.path, modelId)
    return true
end

function engineReplaceModel(dff, modelId)
    record("engineReplaceModel", dff and dff.path, modelId)
    return true
end

function engineRestoreModel(modelId)
    record("engineRestoreModel", modelId)
    return true
end

function engineRestoreCOL(modelId)
    record("engineRestoreCOL", modelId)
    return true
end

function engineGetModelNameFromID(modelId)
    record("engineGetModelNameFromID", modelId)
    return "spider_allocated"
end

function engineGetModelTextureNames(modelName)
    record("engineGetModelTextureNames", modelName)
    return { "box", "spider_eye", "i_sh3", "spider_teeth", "i" }
end

-----------------------------------------------------------------------------
-- elements
-----------------------------------------------------------------------------
function isElement(element)
    return type(element) == "table" and element.__element == true
end

function createObject(modelId, x, y, z, rx, ry, rz)
    record("createObject", modelId, x, y, z, rx, ry, rz)
    local object = {
        __element = true,
        type = "object",
        model = modelId,
        x = x, y = y, z = z,
        rx = rx or 0, ry = ry or 0, rz = rz or 0,
        dimension = 0, interior = 0, doubleSided = false,
    }
    _state.objects[_state.nextObject] = object
    object.id = _state.nextObject
    _state.nextObject = _state.nextObject + 1
    return object
end

function destroyElement(element)
    record("destroyElement", element and element.id)
    if element then element.destroyed = true end
    return true
end

function setElementDoubleSided(element, setting)
    record("setElementDoubleSided", element and element.id, setting)
    if element then element.doubleSided = setting end
    return true
end

function setElementDimension(element, dimension)
    record("setElementDimension", element and element.id, dimension)
    if element then element.dimension = dimension end
    return true
end

function setElementInterior(element, interior)
    record("setElementInterior", element and element.id, interior)
    if element then element.interior = interior end
    return true
end

function setElementRotation(element, rx, ry, rz)
    record("setElementRotation", element and element.id, rx, ry, rz)
    if element then element.rx, element.ry, element.rz = rx, ry, rz end
    return true
end

function setElementPosition(element, x, y, z)
    record("setElementPosition", element and element.id, x, y, z)
    if element then element.x, element.y, element.z = x, y, z end
    return true
end

local player = { __element = true, type = "player", x = 100.0, y = 200.0, z = 10.0, rz = 0 }
localPlayer = player

function getElementPosition(element)
    if element == player then return player.x, player.y, player.z end
    if element and element.x then return element.x, element.y, element.z end
    return 0, 0, 0
end

function getElementRotation(element)
    if element == player then return 0, 0, player.rz end
    if element and element.rz then return element.rx or 0, element.ry or 0, element.rz end
    return 0, 0, 0
end

function getElementDimension(element)
    return element and element.dimension or 0
end

function getElementInterior(element)
    return element and element.interior or 0
end

function getElementMatrix(element, legacy)
    record("getElementMatrix", element and element.id, legacy)
    if element ~= player then return nil end
    -- right, forward, up, position  (forward = +Y for rz 0)
    return {
        { 1, 0, 0, 0 },
        { 0, 1, 0, 0 },
        { 0, 0, 1, 0 },
        { player.x, player.y, player.z, 1 },
    }
end

-----------------------------------------------------------------------------
-- camera / world
-----------------------------------------------------------------------------
function getCameraMatrix()
    -- camera 5 m behind and 3 m above the player, looking north
    return player.x, player.y - 5.0, player.z + 3.0, player.x, player.y + 10.0, player.z, 70
end

function guiGetScreenSize()
    return 1280, 720
end

function getWorldFromScreenPosition(screenX, screenY, depth)
    record("getWorldFromScreenPosition", screenX, screenY, depth)
    return player.x, player.y + depth, player.z
end

function processLineOfSight(fromX, fromY, fromZ, toX, toY, toZ, ...)
    record("processLineOfSight", fromX, fromY, fromZ, toX, toY, toZ, ...)
    -- pretend the ground is exactly 10 m below the aim point
    return true, toX, toY, 5.0, false, 0, 0, 1, 3, 255, -1, false, false, false, false, false
end

function getGroundPosition(x, y, z)
    record("getGroundPosition", x, y, z)
    return 5.0
end

-----------------------------------------------------------------------------
-- events / commands / timers
-----------------------------------------------------------------------------
function addCommandHandler(name, handler, restricted, console)
    _state.commands[name] = handler
    record("addCommandHandler", name)
    return true
end

function addEvent(name, allowRemote)
    _state.events[name] = true
    record("addEvent", name, allowRemote)
    return true
end

function addEventHandler(name, element, handler)
    _state.handlers[name] = handler
    record("addEventHandler", name)
    return true
end

function triggerServerEvent(name, ...)
    record("triggerServerEvent", name, ...)
    return true
end

function setTimer(fn, interval, repeats)
    record("setTimer", interval, repeats)
    fn()                                     -- run immediately for the test
    return { __element = true, type = "timer" }
end

function getPlayerName(element)
    return "TestPlayer"
end

resourceRoot = { __element = true, type = "resource" }
root = { __element = true, type = "root" }
source = nil
client = nil

-- helper used by the test harness
function _fireEvent(name, ...)
    local handler = _state.handlers[name]
    if not handler then error("no handler registered for " .. tostring(name)) end
    return handler(...)
end

function _runCommand(name, ...)
    local handler = _state.commands[name]
    if not handler then error("no command handler for " .. tostring(name)) end
    return handler(player, name, ...)
end
