GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.VehicleManager = { activeVehicle = nil, activeSpec = nil, states = setmetatable({}, { __mode = "k" }), started = false }
local V = G4.VehicleManager

local function notify(text, r, g, b)
    if G4.notify then G4.notify(text, r, g, b) end
end

function V.activate(vehicle)
    if not isElement(vehicle) or getElementType(vehicle) ~= "vehicle" then return false end
    local model = getElementModel(vehicle)
    if V.activeVehicle and V.activeVehicle ~= vehicle then V.release(V.activeVehicle) end
    local spec = G4.VehicleDatabase.get(model)
    if not spec then
        V.activeVehicle, V.activeSpec, G4.State.activeVehicle, G4.State.activeModel = nil, nil, nil, nil
        notify("No GTA IV-style estimate exists for this model; native MTA handling is left unchanged.", 255, 190, 120)
        return false
    end
    V.activeVehicle, V.activeSpec = vehicle, spec
    G4.State.activeVehicle, G4.State.activeModel = vehicle, model
    V.states[vehicle] = G4.PhysicsCore.newState(spec, G4.State.profile)
    V.states[vehicle].lod = "FULL"
    if G4.State.enabled then G4.Adapter.applyNativeBase(vehicle, spec, G4.State.profile) end
    G4.Performance.updateLods(true)
    G4.log(string.format("FULL LOD active: %s (%d), database entry estimated=%s.", spec.name, model, tostring(spec.estimated)))
    return true
end

function V.release(vehicle)
    if not vehicle then return end
    if isElement(vehicle) and G4.Config.handling.restoreOnExit then G4.Adapter.restoreNative(vehicle) end
    V.states[vehicle] = nil
    if V.activeVehicle == vehicle then
        V.activeVehicle, V.activeSpec = nil, nil
        G4.State.activeVehicle, G4.State.activeModel = nil, nil
    end
end

function V.setEnabled(enabled)
    G4.State.enabled = enabled == true
    local vehicle, spec = V.activeVehicle, V.activeSpec
    if isElement(vehicle) and spec then
        if G4.State.enabled then
            G4.Adapter.applyNativeBase(vehicle, spec, G4.State.profile)
        else
            G4.Adapter.restoreNative(vehicle)
            local state = V.states[vehicle]
            if state then state.accumulator = 0 end
        end
    end
    G4.Performance.updateLods(true)
    notify("Physics emulator " .. (G4.State.enabled and "enabled." or "disabled; native physics restored."))
    return G4.State.enabled
end

function V.setProfile(name)
    name = tostring(name or ""):lower()
    if not G4.Config.profiles[name] then return false end
    G4.State.profile = name
    if isElement(V.activeVehicle) and V.activeSpec then
        local state = V.states[V.activeVehicle]
        if state then state.profile = name end
        if G4.State.enabled then G4.Adapter.applyNativeBase(V.activeVehicle, V.activeSpec, name) end
    end
    notify("Profile applied: " .. G4.Config.profiles[name].label)
    return true
end

function V.resetCurrent()
    local vehicle = V.activeVehicle
    if not isElement(vehicle) or not V.activeSpec then return false end
    V.states[vehicle] = G4.PhysicsCore.newState(V.activeSpec, G4.State.profile)
    if G4.State.enabled then G4.Adapter.applyNativeBase(vehicle, V.activeSpec, G4.State.profile) end
    G4.log("Internal wheel, shift, ABS and prediction state reset; vehicle position was not changed.")
    return true
end

function V.reloadCurrent()
    local vehicle = V.activeVehicle
    if not isElement(vehicle) then return false end
    local spec = G4.VehicleDatabase.get(getElementModel(vehicle))
    if not spec then return false end
    G4.Adapter.restoreNative(vehicle)
    V.activeSpec = spec
    V.states[vehicle] = G4.PhysicsCore.newState(spec, G4.State.profile)
    if G4.State.enabled then G4.Adapter.applyNativeBase(vehicle, spec, G4.State.profile) end
    if G4.Calibration then G4.Calibration.load() end
    return true
end

local function activateFromSeat(ped, seat)
    if ped ~= localPlayer or seat ~= 0 then return end
    V.activate(source)
end

local function onVehicleExit(ped, seat)
    if ped ~= localPlayer then return end
    V.release(source)
end

local function onCollision(hitElement, impulse, bodyPart, x, y, z, nx, ny, nz)
    if source == V.activeVehicle then
        G4.Collision.onImpact(source, hitElement, impulse, x, y, z, nx, ny, nz)
    end
end

local function onDestroy()
    if source == V.activeVehicle then
        V.states[source] = nil
        V.activeVehicle, V.activeSpec = nil, nil
        G4.State.activeVehicle, G4.State.activeModel = nil, nil
    else
        V.states[source] = nil
    end
end

local function canRun(vehicle)
    if not G4.State.enabled or not isElement(vehicle) or getVehicleController(vehicle) ~= localPlayer then return false end
    if type(isElementSyncer) == "function" then
        local ok, syncer = pcall(isElementSyncer, vehicle)
        if ok and not syncer then return false end
    end
    return true
end

local function onPreRender(timeSlice)
    G4.Performance.updateLods()
    G4.Performance.processRemoteLods()
    local vehicle = V.activeVehicle
    local state = vehicle and V.states[vehicle]
    if not state or not canRun(vehicle) then return end
    local frameDt = M.clamp((tonumber(timeSlice) or 16.7) / 1000, 0, G4.Config.maxFrameDelta)
    state.accumulator = math.min((state.accumulator or 0) + frameDt, G4.Config.fixedStep * G4.Config.maxSubsteps)
    local steps, startedAt = 0, getTickCount()
    while state.accumulator >= G4.Config.fixedStep and steps < G4.Config.maxSubsteps do
        G4.PhysicsCore.step(vehicle, state, G4.Config.fixedStep)
        state.accumulator = state.accumulator - G4.Config.fixedStep
        steps = steps + 1
    end
    if steps > 0 then G4.Performance.recordStep(getTickCount() - startedAt) end
end

function V.start()
    if V.started then return end
    V.started = true
    addEventHandler("onClientVehicleEnter", root, activateFromSeat)
    addEventHandler("onClientVehicleExit", root, onVehicleExit)
    addEventHandler("onClientVehicleCollision", root, onCollision)
    addEventHandler("onClientElementDestroy", root, onDestroy)
    addEventHandler("onClientPreRender", root, onPreRender)
    if G4.Sync then G4.Sync.startClient() end
    local vehicle = getPedOccupiedVehicle(localPlayer)
    if vehicle and getPedOccupiedVehicleSeat(localPlayer) == 0 then V.activate(vehicle) end
    G4.Performance.updateLods(true)
end

function V.stop()
    if not V.started then return end
    removeEventHandler("onClientVehicleEnter", root, activateFromSeat)
    removeEventHandler("onClientVehicleExit", root, onVehicleExit)
    removeEventHandler("onClientVehicleCollision", root, onCollision)
    removeEventHandler("onClientElementDestroy", root, onDestroy)
    removeEventHandler("onClientPreRender", root, onPreRender)
    if G4.Sync then G4.Sync.stopClient() end
    if isElement(V.activeVehicle) then G4.Adapter.restoreNative(V.activeVehicle) end
    V.activeVehicle, V.activeSpec = nil, nil
    V.states = setmetatable({}, { __mode = "k" })
    G4.State.activeVehicle, G4.State.activeModel = nil, nil
    V.started = false
end
