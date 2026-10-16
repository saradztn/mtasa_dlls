-- Royal Fortress server entry (remake)
-- ACL-gated interaction: hasObjectPermissionTo is used to check rights.
function rfHasRight(player, right)
    return hasObjectPermissionTo(player, right, false) == true
end
