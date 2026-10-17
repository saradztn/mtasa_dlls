PSG={objects={},ids={},resources={},shaders={},panelObjects={},quality='HIGH',materialStatus={}}
function PSG.keep(e)
    if isElement(e) then table.insert(PSG.resources,e) end
    return e
end
function PSG.clearMaterials()
    for _,s in ipairs(PSG.shaders) do if isElement(s) then destroyElement(s) end end
    PSG.shaders={}
    for _,e in ipairs(PSG.materialResources or {}) do if isElement(e) then destroyElement(e) end end
    PSG.materialResources={};PSG.materialStatus={}
end
function PSG.loadMaterials()
    PSG.clearMaterials()
    local q=PSG_CONFIG.quality[PSG.quality]
    local groups={concrete='concrete',industrial='concrete',floor='floor',steel='metal',frame='metal',rope='rope',glass='glass',asphalt='asphalt',warning='floor',rubber='rope',door='metal',bolt='metal',cyan='metal',pink='metal',amber='metal',signage='metal'}
    for material,kind in pairs(groups) do
        local s,technique=dxCreateShader('shaders/'..kind..'.fx',0,160,false,'object')
        local normal,surface,reason
        if not s then reason='shader compilation/allocation failed'
        else
            normal=dxCreateTexture('textures/'..q.tier..'/'..material..'_normal.png','argb',true,'wrap')
            surface=dxCreateTexture('textures/'..q.tier..'/'..material..'_surface.png','argb',true,'wrap')
            if not normal or not surface then reason='normal/surface allocation failed'
            else
                local ok,configured=pcall(function()
                    if not dxSetShaderValue(s,'gNormal',normal) or not dxSetShaderValue(s,'gSurface',surface)
                        or not dxSetShaderValue(s,'gReflection',q.reflections) or not dxSetShaderValue(s,'gNormalScale',q.normal)
                        or not dxSetShaderValue(s,'gEmissive',(material=='cyan' or material=='pink' or material=='amber') and 1.8 or 0) then return false end
                    for _,ob in ipairs(PSG.objects) do
                        if not engineApplyShaderToWorldTexture(s,'psg_'..material,ob) then return false end
                    end
                    return true
                end)
                if not ok or not configured then reason='parameter/texture binding failed: '..tostring(configured) end
            end
        end
        if reason then
            if isElement(s) then destroyElement(s) end
            if isElement(normal) then destroyElement(normal) end
            if isElement(surface) then destroyElement(surface) end
            PSG.materialStatus[material]={state='fallback',reason=reason}
            outputDebugString('[PSG] '..material..': '..reason..'; using TXD/prelight',1)
        else
            table.insert(PSG.materialResources,normal);table.insert(PSG.materialResources,surface);table.insert(PSG.shaders,s)
            PSG.materialStatus[material]={state='active',technique=technique}
            outputDebugString('[PSG] '..material..': '..tostring(technique))
        end
    end
end
