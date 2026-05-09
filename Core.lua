local ADDON_NAME, ns = ...

ns.VERSION = "0.4.2-alpha"
ns.ADDON_NAME = ADDON_NAME

local defaults = {
    seen = {},
    minimap = {
        hide = false,
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
    local db = ns.GetDB()
    db.seen[id] = time()
end

function ns.IsSeen(id)
    local db = ns.GetDB()
    return id and db.seen[id] ~= nil
end

local function InitMinimap()
    local LibStub = _G.LibStub
    if not LibStub then return end

    local LDB = LibStub("LibDataBroker-1.1", true)
    local DBIcon = LibStub("LibDBIcon-1.0", true)

    if not LDB or not DBIcon then
        print("|cffb26cffAlterTime News:|r LibDataBroker/LibDBIcon no disponibles.")
        return
    end

    local broker = LDB:NewDataObject("AlterTimeNews", {
        type = "launcher",
        text = "AlterTime News",
        icon = "Interface\\AddOns\\AltertimeAddon\\Media\\AltertimeLogo.blp",
        OnClick = function()
            ns.Toggle()
        end,
        OnTooltipShow = function(tooltip)
            tooltip:AddLine("AlterTime News")
            tooltip:AddLine("Clic para abrir/cerrar noticias.", 1, 1, 1)
        end,
    })

    DBIcon:Register("AlterTimeNews", broker, ns.GetDB().minimap)
end

local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("ADDON_LOADED")
eventFrame:SetScript("OnEvent", function(_, event, addonName)
    if event ~= "ADDON_LOADED" or addonName ~= ADDON_NAME then return end

    ns.GetDB()
    InitMinimap()

    SLASH_ALTERTIMENEWS1 = "/altertime"
    SLASH_ALTERTIMENEWS2 = "/atnews"
    SlashCmdList.ALTERTIMENEWS = function()
        ns.Toggle()
    end
end)
