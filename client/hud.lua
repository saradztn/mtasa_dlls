-- minimal HUD / commands
addCommandHandler("castlelist", function(cmd, page, filter)
    outputChatBox("Royal Fortress rooms (page 1)")
    for i = 1, 12 do outputChatBox(string.format("%d - Room %d", i, i)) end
end)
addCommandHandler("castlehelp", function()
    outputChatBox("Royal Fortress commands:")
    outputChatBox("/castle /castleinterior /showp /castleroom <id>")
    outputChatBox("/castletime <hour|auto>")
end)
