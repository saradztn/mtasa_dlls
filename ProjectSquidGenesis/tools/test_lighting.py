"""Exercise actual lighting.lua with deterministic camera input. No graphics rendering."""
from pathlib import Path
import json
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
vm=LuaRuntime(unpack_returned_tuples=True)
vm.execute('''
PSG={shaders={'test'},quality='HIGH'}
PSG_CONFIG={dimension=2601,origin={0,0,0},quality={HIGH={lightCount=2},LOW={lightCount=1}},lights={
{position={0,0,3},color={.1,.8,1}}, {position={2,0,3},color={1,.1,.4}},
{position={100,0,3},color={.8,.6,.2}}, {position={102,0,3},color={.2,.9,.7}}}}
localPlayer={};camera={0,0,1};dimension=2601;uniforms={}
function getElementDimension()return dimension end
function getCameraMatrix()return unpack(camera)end
function dxSetShaderValue(shader,name,...)uniforms[name]={...};return true end
''')
vm.execute((ROOT/'client/lighting.lua').read_text())
vm.execute('''
for i=1,10 do PSG.updateLighting(.1) end
assert(PSG.lightSlots[1].index==1 and PSG.lightSlots[2].index==2)
assert(PSG.lightSlots[1].weight==1 and PSG.lightSlots[2].weight==1)
-- A small camera movement near the nearest-light boundary should keep current fixtures.
camera={51,0,1};PSG.updateLighting(.1)
assert(PSG.lightSlots[1].index==1 and PSG.lightSlots[2].index==2,'hysteresis failed')
camera={101,0,1};changes=0
for frame=1,30 do
    local old={};for i=1,4 do old[i]=PSG.lightSlots[i].index end
    PSG.updateLighting(.1)
    local occupied={}
    for i=1,4 do
        local slot=PSG.lightSlots[i]
        assert(slot.weight>=0 and slot.weight<=1)
        if slot.index~=old[i] then assert(slot.weight==0,'position changed while lit');changes=changes+1 end
        if slot.index then assert(not occupied[slot.index],'duplicate source');occupied[slot.index]=true end
        local uniform=uniforms['gLight'..(i-1)];local color=uniforms['gColor'..(i-1)]
        if slot.index then
            local source=PSG_CONFIG.lights[slot.index]
            for j=1,3 do
                assert(uniform[j]==source.position[j],'interpolated fictional source position')
                assert(math.abs(color[j]-source.color[j]*slot.weight)<.000001)
            end
        else assert(color[1]==0 and color[2]==0 and color[3]==0,'stale inactive color') end
    end
end
assert(changes==2)
for i=1,2 do assert(PSG.lightSlots[i].index>=3 and PSG.lightSlots[i].weight==1) end
PSG.quality='LOW';for i=1,20 do PSG.updateLighting(.1) end
local active=0;for i=1,4 do if PSG.lightSlots[i].weight>0 then active=active+1 end end;assert(active==1)
local old=PSG.lightSlots[1].weight;dimension=0;PSG.updateLighting(.1);assert(PSG.lightSlots[1].weight==old)
PSG.resetLighting();assert(#PSG.lightSlots==0)
''')
result={'status':'PASS','scope':'Lua mock logic only; no MTA or rendered-light test','tests':['stable source identity under rank-boundary hysteresis','all source-position changes occur at zero slot intensity','fixture positions remain exact, not interpolated through space','slot colors equal source color times bounded fade weight','no duplicate selected source IDs; inactive colors reset to zero','LOW settles to its configured light budget','outside-dimension early return and explicit reset']}
(ROOT/'tests/lighting_results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
