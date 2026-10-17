PSG.wetness=.65
PSG.wetTarget=.65
addCommandHandler('psg_wet',function(_,state)
    local levels={dry=0,slightly=.22,wet=.65,heavy=1,drying=0}
    if not levels[state] then outputChatBox('/psg_wet dry|slightly|wet|heavy|drying');return end
    PSG.wetTarget=levels[state];PSG.drying=state=='drying'
end)
function PSG.updateWetness()
    local step=PSG.drying and .002 or .025
    PSG.wetness=PSG.wetness+math.max(-step,math.min(step,PSG.wetTarget-PSG.wetness))
end
