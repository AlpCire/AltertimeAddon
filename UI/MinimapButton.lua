local ADDON_NAME, ns = ...

local registered = false
local ICON_NAME = "AlterTimeNews"

local function RegisterMinimapButton()
    if registered then return end

    local LibStub = _G.LibStub
    if not LibStub then return end

    local LDB = LibStub("LibDataBroker-1.1", true)
    local DBIcon = LibStub("LibDBIcon-1.0", true)

    if not LDB or not DBIcon then
        print("|cffb26cffAlterTime News:|r LibDataBroker/LibDBIcon no disponibles.")
        return
    end

    local db = ns.GetDB and ns.GetDB() or {}
    db.minimap = db.minimap or {
        hide = false,
        minimapPos = 220,
    }

    local dataObject = LDB:NewDataObject(ICON_NAME, {
        type = "launcher",
        text = "AlterTime News",
        icon = "Interface\\AddOns\\AltertimeAddon\\Media\\AltertimeLogo.tga",

        OnClick = function(_, button)
            if button == "LeftButton" then
                if ns.Toggle then
                    ns.Toggle()
                end
            elseif button == "RightButton" then
                print("|cffb26cffAlterTime News|r")
                print("/altertime - Abrir noticias")
                print("/atnews - Abrir noticias")
                print("/altertime minimap - Mostrar icono")
            end
        end,

        OnTooltipShow = function(tooltip)
            tooltip:AddLine("AlterTime News")
            tooltip:AddLine(" ")
            tooltip:AddLine("Clic izquierdo: abrir/cerrar noticias", 1, 1, 1)
            tooltip:AddLine("Clic derecho: mostrar comandos", 1, 1, 1)
        end,
    })

    local ok, err = pcall(function()
        DBIcon:Register(ICON_NAME, dataObject, db.minimap)
    end)

    if not ok then
        print("|cffb26cffAlterTime News:|r error registrando minimapa:", err)
        return
    end

    function ns.ShowMinimapIcon()
        db.minimap.hide = false
        if DBIcon then
            DBIcon:Show(ICON_NAME)
        end
    end

    function ns.HideMinimapIcon()
        db.minimap.hide = true
        if DBIcon then
            DBIcon:Hide(ICON_NAME)
        end
    end

    registered = true
end

local f = CreateFrame("Frame")
f:RegisterEvent("PLAYER_LOGIN")
f:SetScript("OnEvent", RegisterMinimapButton)
