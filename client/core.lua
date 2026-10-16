-- core: time command
addCommandHandler("castletime", function(cmd, hour)
    if hour == "auto" then
        setMinuteDuration(1000)
        RFClient.timeOverride = false
        return
    end
    local h = tonumber(hour)
    if not h or h < 0 or h > 23 then return end
    setTime(h, 0)
    setMinuteDuration(60000000)
    RFClient.timeOverride = true
end)
