local ADDON_NAME, ns = ...

ns.VERSION = "auto-18"
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

local function InitMinimap()
    local LibStub = _G.LibStub
    if not LibStub then
        print("|cffb26cffAlterTime News:|r LibStub no disponible.")
        return
    end

    local LDB = LibStub("LibDataBroker-1.1", true)
    local DBIcon = LibStub("LibDBIcon-1.0", true)

    if not LDB or not DBIcon then
        print("|cffb26cffAlterTime News:|r LibDataBroker/LibDBIcon no disponibles.")
        return
    end

    local broker = LDB:NewDataObject("AlterTimeNews", {
        type = "launcher",
        text = "AlterTime News",
        icon = "Interface\\AddOns\\AltertimeAddon\\Media\\AltertimeLogo.tga",
        OnClick = function(_, button)
            if button == "LeftButton" then
                ns.Toggle()
            elseif button == "RightButton" then
                local db = ns.GetDB()
                db.minimap.hide = not db.minimap.hide

                if db.minimap.hide then
                    DBIcon:Hide("AlterTimeNews")
                    print("|cffb26cffAlterTime News:|r icono del minimapa oculto. Usa /altertime minimap para mostrarlo.")
                end
            end
        end,
        OnTooltipShow = function(tooltip)
            tooltip:AddLine("AlterTime News")
            tooltip:AddLine("Clic izquierdo: abrir/cerrar noticias", 1, 1, 1)
            tooltip:AddLine("Clic derecho: ocultar icono", 1, 1, 1)
        end,
    })

    DBIcon:Register("AlterTimeNews", broker, ns.GetDB().minimap)
end

local function HandleSlash(msg)
    msg = string.lower(msg or "")

    if msg == "minimap" then
        local LibStub = _G.LibStub
        local DBIcon = LibStub and LibStub("LibDBIcon-1.0", true)
        local db = ns.GetDB()

        db.minimap.hide = false

        if DBIcon then
            DBIcon:Show("AlterTimeNews")
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
    InitMinimap()

    SLASH_ALTERTIMENEWS1 = "/altertime"
    SLASH_ALTERTIMENEWS2 = "/atnews"
    SlashCmdList.ALTERTIMENEWS = HandleSlash

    print("|cffb26cffAlterTime News|r cargado. Usa /altertime o el icono del minimapa.")
end)
