-- Server-side permission gate for future protected palace actions.
local function hasPalaceRight(player, right)
 if not isElement(player) or getElementType(player)~='player' then return false end
 local account=getPlayerAccount(player)
 if not account or isGuestAccount(account) then return false end
 local group=right=='vault' and 'RoyalPalaceVault' or right=='archive' and 'RoyalPalaceArchive' or 'RoyalPalaceGate'
 return hasObjectPermissionTo('user.'..getAccountName(account),'function.kickPlayer',false) or isObjectInACLGroup('user.'..getAccountName(account),aclGetGroup(group) or createACLGroup(group))
end
addEvent('royalpalace:request',true)
addEventHandler('royalpalace:request',root,function(action)
 local p=client
 if action~='teleport' and action~='mechanism' then return end
 if not isElement(p) then return end
 -- No privileged mutation is accepted without a configured role.
 if not hasPalaceRight(p,'gate') then outputChatBox('لا تملك صلاحية هذا الإجراء.',p,220,100,80); return end
 outputChatBox('تم رفض الإجراء: لا يوجد إجراء إداري عام مفعّل.',p,220,180,120)
end)
