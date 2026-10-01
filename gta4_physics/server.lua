GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics

local function startServer()
    if G4.Sync then G4.Sync.startServer() end
    outputDebugString(string.format("[GTA4P %s] Server validation/sync active; force simulation stays with the vehicle's local MTA syncer.", G4.VERSION), 3, 120, 220, 255)
end

local function stopServer()
    if G4.Sync then G4.Sync.stopServer() end
end

addEventHandler("onResourceStart", resourceRoot, startServer)
addEventHandler("onResourceStop", resourceRoot, stopServer)
