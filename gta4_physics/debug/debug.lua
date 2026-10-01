GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
G4.Debug = { started = false }

function G4.Debug.start()
    if G4.Debug.started then return end
    G4.Debug.started = true
    addEventHandler("onClientRender", root, G4.Visualizer.render)
end

function G4.Debug.stop()
    if not G4.Debug.started then return end
    removeEventHandler("onClientRender", root, G4.Visualizer.render)
    G4.Debug.started = false
end
