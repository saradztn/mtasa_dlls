RFMech = { parts = {}, states = {}, prompt = nil }

function RFMech.stream()
    for id, meta in pairs(RFScene.data.interactive) do
        RFMech.states[id] = (meta.default == "open")
        for i, part in ipairs(meta.parts) do
            local key = id .. "#" .. i
            local mid = RFScene.modelIds[part.model]
            if mid then
                local o = createObject(mid, part.pos[1], part.pos[2], part.pos[3], part.rot[1], part.rot[2], part.rot[3])
                o.rz = part.rot[3]
                RFMech.parts[key] = { element = o, part = part, id = id }
            end
        end
    end
end

addEventHandler("rf:states", resourceRoot, function(list)
    for _, pair in ipairs(list) do
        RFMech.states[pair[1]] = pair[2]
    end
end)

addEventHandler("rf:state", resourceRoot, function(id, value, broadcast)
    RFMech.states[id] = value
    local meta = RFScene.data.interactive[id]
    if not meta then return end
    for i, part in ipairs(meta.parts) do
        local key = id .. "#" .. i
        local info = RFMech.parts[key]
        if info then
            local e = info.element
            local move = part.open.move or {0,0,0}
            local rot = part.open.rot or {0,0,0}
            if value then
                moveObject(e, RFConfig.animTime, part.pos[1]+move[1], part.pos[2]+move[2], part.pos[3]+move[3], rot[1], rot[2], rot[3])
            else
                moveObject(e, RFConfig.animTime, part.pos[1], part.pos[2], part.pos[3], part.rot[1], part.rot[2], part.rot[3])
            end
        end
    end
end)

-- prompt updater
setTimer(function()
    local x,y,z = getElementPosition(localPlayer)
    local best, bestdist, bestid = nil, 1e18, nil
    for key, info in pairs(RFMech.parts) do
        local e = info.element
        local d = (e.x-x)^2 + (e.y-y)^2 + (e.z-z)^2
        if d < bestdist then bestdist = d; bestid = info.id end
    end
    if bestdist <= 25 then
        RFMech.prompt = { id = bestid }
    else
        RFMech.prompt = nil
    end
end, 300, 0)

bindKey("e", "down", function()
    if RFMech.prompt then
        triggerServerEvent("rf:interact", resourceRoot, RFMech.prompt.id)
    end
end)
