local ADDON_NAME, ns = ...

ns.VERSION = "auto-25"
ns.ADDON_NAME = ADDON_NAME

local defaults = {
    seen = {},
    minimap = {
        hide = false,
        minimapPos = 220,
    },
}

local function CopyDefaults(src, dst)
    if type(dst) ~= "table" then
        dst = {}
    end

    for k, v in pairs(src) do
        if type(v) == "table" then
            dst[k] = CopyDefaults(v, dst[k])
        elseif dst[k] == nil then
            dst[k] = v
        end
    end

    return dst
end

function ns.GetDB()
    AltertimeAddonDB = CopyDefaults(defaults, AltertimeAddonDB)
    return AltertimeAddonDB
end

function ns.Toggle()
    if ns.MainFrame and ns.MainFrame:IsShown() then
        ns.MainFrame:Hide()
    elseif ns.ShowMainFrame then
        ns.ShowMainFrame()
    end
end

function ns.MarkSeen(id)
    if not id then return end
    ns.GetDB().seen[id] = time()
end

function ns.IsSeen(id)
    return id and ns.GetDB().seen[id] ~= nil
end

local function HandleSlash(msg)
    msg = string.lower(msg or "")

    if msg == "minimap" then
        local db = ns.GetDB()
        db.minimap.hide = false

        if ns.ShowMinimapIcon then
            ns.ShowMinimapIcon()
        end

        print("|cffb26cffAlterTime News:|r icono del minimapa mostrado.")
        return
    end

    ns.Toggle()
end

local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("ADDON_LOADED")
eventFrame:SetScript("OnEvent", function(_, event, addonName)
    if event ~= "ADDON_LOADED" or addonName ~= ADDON_NAME then return end

    ns.GetDB()

    SLASH_ALTERTIMENEWS1 = "/altertime"
    SLASH_ALTERTIMENEWS2 = "/atnews"
    SlashCmdList.ALTERTIMENEWS = HandleSlash

    print("|cffb26cffAlterTime News|r cargado. Usa /altertime o el icono del minimapa.")
end)
