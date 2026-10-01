local AR = AdvancedRendering
AR.Materials = {
    worldShaders = {},
    vehicleShader = nil,
    currentVehicle = nil,
    started = false
}

local function createWorldShader(path, label, elementTypes)
    local shader, technique = dxCreateShader(path, 0, 0, false, elementTypes or "world")
    if not isElement(shader) then
        AR.log("Could not create " .. label .. " shader from " .. path .. ". Check debugscript 3 for the HLSL compiler message.", 1)
        return nil
    end
    AR.log(label .. " shader created (technique " .. tostring(technique or "unknown") .. ").")
    return shader
end

local function removeWorldClass(name)
    local entry = AR.Materials.worldShaders[name]
    if not entry then
        return
    end
    for _, pattern in ipairs(entry.patterns or {}) do
        if isElement(entry.shader) then
            engineRemoveShaderFromWorldTexture(entry.shader, pattern)
        end
    end
    if isElement(entry.shader) then
        destroyElement(entry.shader)
    end
    AR.Materials.worldShaders[name] = nil
end

local function applyWorldClass(name, config)
    local shader = createWorldShader("shaders/materials.fx", "material " .. name)
    if not shader then
        return false
    end
    dxSetShaderValue(shader, "MaterialResponse", tonumber(config.response) or 0)
    dxSetShaderValue(shader, "MaterialRoughness", tonumber(config.roughness) or 1)
    local tint = config.tint or { 1, 1, 1 }
    dxSetShaderValue(shader, "MaterialTint", tonumber(tint[1]) or 1, tonumber(tint[2]) or 1, tonumber(tint[3]) or 1)

    local appliedPatterns = {}
    for _, pattern in ipairs(config.patterns or {}) do
        local ok = engineApplyShaderToWorldTexture(shader, pattern)
        if ok then
            appliedPatterns[#appliedPatterns + 1] = pattern
        end
    end

    AR.Materials.worldShaders[name] = {
        shader = shader,
        patterns = config.patterns or {},
        appliedPatterns = appliedPatterns
    }
    AR.log("Material class '" .. name .. "' is active for " .. #appliedPatterns .. " texture pattern(s). Texture-name matching is best-effort on custom maps.")
    return true
end

local function clearWorldShaders()
    local names = {}
    for name in pairs(AR.Materials.worldShaders) do
        names[#names + 1] = name
    end
    for _, name in ipairs(names) do
        removeWorldClass(name)
    end
end

local function removeVehicleShader()
    local shader = AR.Materials.vehicleShader
    local vehicle = AR.Materials.currentVehicle
    if isElement(shader) then
        if isElement(vehicle) then
            engineRemoveShaderFromWorldTexture(shader, "vehiclegrunge256", vehicle)
            engineRemoveShaderFromWorldTexture(shader, "?emap*", vehicle)
        end
        destroyElement(shader)
    end
    AR.Materials.vehicleShader = nil
    AR.Materials.currentVehicle = nil
end

local function applyVehicleShader(vehicle)
    if not AR.State.enabled or not AR.State.features.vehicleResponse then
        return false
    end
    if not isElement(vehicle) or getElementType(vehicle) ~= "vehicle" then
        return false
    end

    if AR.Materials.currentVehicle == vehicle and isElement(AR.Materials.vehicleShader) then
        return true
    end
    removeVehicleShader()

    local shader = createWorldShader("shaders/vehicle.fx", "vehicle surface response", "vehicle")
    if not shader then
        return false
    end
    local response = tonumber(AR.State.strengths.vehicle) or 0.07
    dxSetShaderValue(shader, "VehicleResponse", response)
    dxSetShaderValue(shader, "VehicleRoughness", 0.72)
    dxSetShaderValue(shader, "VehicleTint", 1.0, 1.0, 1.0)

    local applied = 0
    if engineApplyShaderToWorldTexture(shader, "vehiclegrunge256", vehicle) then
        applied = applied + 1
    end
    if engineApplyShaderToWorldTexture(shader, "?emap*", vehicle) then
        applied = applied + 1
    end
    AR.Materials.vehicleShader = shader
    AR.Materials.currentVehicle = vehicle
    AR.log("Vehicle surface response attached to the local vehicle using " .. applied .. " texture pattern(s). This is a restrained Fresnel/specular accent, not a full dynamic environment reflection.")
    return true
end

function AR.Materials.syncWorldMaterials()
    clearWorldShaders()
    if not AR.State.enabled or not AR.State.features.materialEnhancement then
        return
    end

    for name, config in pairs(AR.Config.materialClasses) do
        applyWorldClass(name, config)
    end
end

function AR.Materials.syncVehicle()
    if not AR.State.enabled or not AR.State.features.vehicleResponse then
        removeVehicleShader()
        return
    end
    local vehicle = getPedOccupiedVehicle(localPlayer)
    if isElement(vehicle) then
        applyVehicleShader(vehicle)
    else
        removeVehicleShader()
    end
end

function AR.Materials.setFeature(name, enabled)
    if name == "materialEnhancement" then
        AR.State.features.materialEnhancement = enabled == true
        AR.Materials.syncWorldMaterials()
        return true
    elseif name == "vehicleResponse" then
        AR.State.features.vehicleResponse = enabled == true
        AR.Materials.syncVehicle()
        return true
    end
    return false
end

function AR.Materials.start()
    if AR.Materials.started then
        return
    end
    AR.Materials.started = true
    addEventHandler("onClientVehicleEnter", root, function(player)
        if player == localPlayer then
            AR.Materials.syncVehicle()
        end
    end)
    addEventHandler("onClientVehicleExit", root, function(player)
        if player == localPlayer then
            removeVehicleShader()
        end
    end)
    AR.Materials.syncWorldMaterials()
    AR.Materials.syncVehicle()
end

function AR.Materials.stop()
    clearWorldShaders()
    removeVehicleShader()
    AR.Materials.started = false
end
