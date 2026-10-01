--[[
    spider_sa / tools/mta_stub_server.lua

    Minimal server-side MTA:SA API mock for tools/smoke_test.js.  It records
    every call in _calls so the test can assert on triggerClientEvent traffic.
    Development aid only - never loaded by the game.
]]

_calls = { order = {} }
_state = {
    commands = {},
    handlers = {},
    events = {},
    triggered = {},        -- eventName -> list of { target = , args = { ... } }
}

local function record(name, ...)
    table.insert(_calls.order, { name = name, args = { ... } })
end

function outputChatBox(text, r, g, b)
    record("outputChatBox", text, r, g, b)
    return true
end

function outputDebugString(text)
    record("outputDebugString", text)
    return true
end

function addCommandHandler(name, handler)
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

function triggerClientEvent(name, sourceElement, target, ...)
    local args = { ... }
    record("triggerClientEvent", name, tostring(args[1]), tostring(args[2]),
        tostring(args[3]), tostring(args[4]))
    if not _state.triggered[name] then _state.triggered[name] = {} end
    table.insert(_state.triggered[name], args)
    return true
end

function isElement(element)
    return type(element) == "table" and element.__element == true
end

local player = { __element = true, type = "player", name = "TestPlayer", x = 100.0, y = 200.0, z = 10.0, rz = 0 }
testPlayer = player

function getPlayerName(element)
    return element and element.name or "unknown"
end

function getElementPosition(element)
    if element and element.x then return element.x, element.y, element.z end
    return 0, 0, 0
end

function getElementRotation(element)
    if element and element.rz then return 0, 0, element.rz end
    return 0, 0, 0
end

function getElementMatrix(element, legacy)
    if element ~= player then return nil end
    return {
        { 1, 0, 0, 0 },                                    -- right  = +X
        { 0, 1, 0, 0 },                                    -- forward = +Y
        { 0, 0, 1, 0 },                                    -- up
        { player.x, player.y, player.z, 1 },
    }
end

function getGroundPosition(x, y, z)
    record("getGroundPosition", x, y, z)
    return 5.0
end

function setTimer(fn, interval, repeats)
    record("setTimer", interval, repeats)
    fn()
    return { __element = true, type = "timer" }
end

root = { __element = true, type = "root" }
resourceRoot = { __element = true, type = "resource" }
source = nil
client = nil

function _runCommand(name, ...)
    local handler = _state.commands[name]
    if not handler then error("no command handler for " .. tostring(name)) end
    return handler(player, name, ...)
end

function _fireEvent(name, element, ...)
    local handler = _state.handlers[name]
    if not handler then error("no handler for " .. tostring(name)) end
    source = element
    local result = handler(...)
    source = nil
    return result
end

function _triggered(name)
    return _state.triggered[name] or {}
end
