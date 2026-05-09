local ADDON_NAME, ns = ...

local LDB = LibStub("LibDataBroker-1.1"):NewDataObject("AlterTimeNews", {
    type = "data source",
    text = "AlterTime News",
    icon = "Interface\\AddOns\\AltertimeAddon\\Media\\AltertimeLogo.tga",

    OnClick = function(self, button)
        if button == "LeftButton" then
            if ns.Toggle then
                ns.Toggle()
            elseif ns.ShowMainFrame then
                ns.ShowMainFrame()
            end
        elseif button == "RightButton" then
            print("|cffb26cffAlterTime News|r")
            print("/altertime - Abrir noticias")
            print("/atnews - Abrir noticias")
        end
    end,

    OnTooltipShow = function(tooltip)
        tooltip:AddLine("AlterTime News")
        tooltip:AddLine(" ")
        tooltip:AddLine("Left Click: Abrir noticias")
        tooltip:AddLine("Right Click: Mostrar comandos")
    end,
})

local icon = LibStub("LibDBIcon-1.0")
local f = CreateFrame("Frame")

f:RegisterEvent("PLAYER_LOGIN")

f:SetScript("OnEvent", function()
    AltertimeAddonDB = AltertimeAddonDB or {}
    AltertimeAddonDB.minimap = AltertimeAddonDB.minimap or {
        hide = false,
        minimapPos = 220,
    }

    icon:Register("AlterTimeNews", LDB, AltertimeAddonDB.minimap)
end)