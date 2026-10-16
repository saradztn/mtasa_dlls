RFScene = { data = nil, objects = {}, byElement = {}, modelIds = {}, loaded = false }
RFClient = { ready = false, active = false, pending = nil, water = nil, timeOverride = false }
for _, _e in ipairs({"rf:prepare","rf:committed","rf:finished","rf:leave","rf:rollback","rf:reload","rf:states","rf:state","rf:debug"}) do
    addEvent(_e, true)
end

-- load world
local function loadWorld()
    local f = fileOpen("client/data/world.json")
    local raw = fileRead(f, fileGetSize(f)); fileClose(f)
    RFScene.data = fromJSON(raw)
end
loadWorld()

-- config defaults
if not RFConfig.streaming then RFConfig.streaming = { maxObjects = 500 } end
if not RFConfig.lights then RFConfig.lights = { maxCoronas = 64 } end

function RFScene.loadAssets(cb, token)
    -- Phase 1: COL
    for name, info in pairs(RFScene.data.models) do
        local id = engineRequestModel("object", 1337)
        RFScene.modelIds[name] = id
        RFModels.loaded[id] = true
        local col = engineLoadCOL("assets/col/" .. name .. ".col")
        if not col then if token then triggerServerEvent("rf:loadFailed", resourceRoot, token, "COL") end; return false end
        local ok = engineReplaceCOL(col, id)
        if not ok then if token then triggerServerEvent("rf:loadFailed", resourceRoot, token, "replaceCOL") end; return false end
    end
    -- Phase 2: TXD (import once per group into first model using it)
    for group, ginfo in pairs(RFScene.data.txds) do
        local txd = engineLoadTXD(ginfo.path, false)
        if not txd then if token then triggerServerEvent("rf:loadFailed", resourceRoot, token, "TXD") end; return false end
        local imported = false
        for name, info in pairs(RFScene.data.models) do
            local has = false
            for _, g in ipairs(info.txds) do if g == group then has = true end end
            if has and not imported then
                local ok = engineImportTXD(txd, RFScene.modelIds[name])
                if not ok then if token then triggerServerEvent("rf:loadFailed", resourceRoot, token, "importTXD") end; return false end
                imported = true
            end
        end
    end
    -- Phase 3: DFF
    for name, info in pairs(RFScene.data.models) do
        local dff = engineLoadDFF("assets/dff/" .. name .. ".dff")
        if not dff then triggerServerEvent("rf:loadFailed", resourceRoot, token, "DFF"); return false end
        local ok = engineReplaceModel(dff, RFScene.modelIds[name])
        if not ok then if token then triggerServerEvent("rf:loadFailed", resourceRoot, token, "replaceDFF") end; return false end
        engineSetModelLODDistance(RFScene.modelIds[name], info.draw, true)
    end
    RFScene.loaded = true
    if cb then cb() end
    return true
end

function RFScene.streamObjects()
    local maxo = RFConfig.streaming.maxObjects
    local count = 0
    for i, obj in ipairs(RFScene.data.objects) do
        if count >= maxo then break end
        local mid = RFScene.modelIds[obj.model]
        if mid then
            local o = createObject(mid, obj.pos[1], obj.pos[2], obj.pos[3], obj.rot[1], obj.rot[2], obj.rot[3])
            RFScene.objects[o] = { index = i, class = obj.class }
            RFScene.byElement[o] = true
            count = count + 1
        end
    end
end

function RFScene.streamMechanisms()
    RFMech.stream()
end

function RFScene.unloadAll()
    -- destroy objects first
    for o, _ in pairs(RFScene.objects) do
        destroyElement(o)
    end
    RFScene.objects = {}
    RFScene.byElement = {}
    for key, info in pairs(RFMech.parts) do
        if isElement(info.element) then destroyElement(info.element) end
    end
    RFMech.parts = {}
    -- then free models
    for id, _ in pairs(RFModels.loaded) do
        engineRestoreModel(id)
        engineRestoreCOL(id)
        engineFreeModel(id)
    end
    RFModels.loaded = {}
    RFScene.modelIds = {}
end

function RFScene.applyEnvironment(active)
    if active then
        setWeather(1)
        setFarClipDistance(1500)
        RFClient.water = createWater(-1400, -1400, 0, 1400, 1400, 0, 0, 0, false)
        setElementDimension(RFClient.water, 779)
    else
        setWeather(3)
        setFarClipDistance(900)
        if RFClient.water and isElement(RFClient.water) then destroyElement(RFClient.water) end
        RFClient.water = nil
    end
end

-- travel state
RFClient.pending = nil

addEventHandler("rf:prepare", resourceRoot, function(token, pos)
    RFClient.pending = { token = token, target = pos }
    local function done()
        RFScene.streamObjects()
        RFScene.streamMechanisms()
        triggerServerEvent("rf:prepared", resourceRoot, token)
    end
    if not RFScene.loaded then
        local ok = RFScene.loadAssets(done, token)
        if ok == false then
            RFClient.pending = nil
        end
    else
        done()
    end
end)

addEventHandler("rf:committed", resourceRoot, function(token, pos)
    if not RFClient.pending or RFClient.pending.token ~= token then return end
    setElementDimension(localPlayer, 779)
    setElementPosition(localPlayer, pos[1], pos[2], pos[3] + 1)
    local hit = processLineOfSight(pos[1], pos[2], pos[3]+1, pos[1], pos[2], pos[3]-1)
    if hit then
        RFScene.applyEnvironment(true)
        RFClient.active = true
        triggerServerEvent("rf:groundReady", resourceRoot, token)
    end
end)

addEventHandler("rf:finished", resourceRoot, function(token)
    if RFClient.pending and RFClient.pending.token == token then
        RFClient.pending = nil
    end
end)

addEventHandler("rf:leave", resourceRoot, function()
    RFScene.applyEnvironment(false)
    RFClient.active = false
    RFClient.pending = nil
    RFScene.unloadAll()
end)

addEventHandler("rf:rollback", resourceRoot, function(token, reason)
    if RFClient.pending and RFClient.pending.token == token then
        RFClient.pending = nil
    end
    RFScene.unloadAll()
    RFScene.loaded = false
end)

addEventHandler("rf:reload", resourceRoot, function(states)
    RFScene.data = RFScene.data
    if states then
        for _, pair in ipairs(states) do
            RFMech.states[pair[1]] = pair[2]
        end
    end
end)

addEventHandler("rf:states", resourceRoot, function(list)
    if list then
        for _, pair in ipairs(list) do
            RFMech.states[pair[1]] = pair[2]
        end
    end
end)

-- hide command
local hidden = false
addCommandHandler("castlehide", function()
    if not hidden then
        -- remove furniture/tree objects
        for o, r in pairs(RFScene.objects) do
            local c = RFScene.data.objects[r.index].class
            if c == "furn" or c == "tree" then
                destroyElement(o)
                RFScene.objects[o] = nil
                RFScene.byElement[o] = nil
            end
        end
        hidden = true
    else
        -- reshown not required
        hidden = false
    end
end)

-- startup
addEventHandler("onClientResourceStart", resourceRoot, function()
    RFClient.ready = true
    triggerServerEvent("rf:hello", resourceRoot, RFConfig.build)
end)
