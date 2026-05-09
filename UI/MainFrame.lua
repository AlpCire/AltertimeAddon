local ADDON_NAME, ns = ...

local WIDTH = 1040
local HEIGHT = 700
local CARD_HEIGHT = 150
local LOGO_PATH = "Interface\\AddOns\\AltertimeAddon\\Media\\AltertimeLogo.tga"

local function CreateFont(parent, size, flags)
    local fs = parent:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    fs:SetFont("Fonts\\FRIZQT__.TTF", size or 12, flags or "")
    fs:SetTextColor(0.92, 0.92, 0.92)
    fs:SetJustifyH("LEFT")
    fs:SetJustifyV("TOP")
    return fs
end

local function ClearChildren(frame)
    if not frame.children then return end
    for _, child in ipairs(frame.children) do
        child:Hide()
        child:SetParent(nil)
    end
    wipe(frame.children)
end

local function AddChild(parent, child)
    parent.children = parent.children or {}
    table.insert(parent.children, child)
end

local function SafeText(value)
    if value == nil then return "" end
    return tostring(value)
end

local function FormatDate(ts)
    if type(ts) ~= "number" then return "" end
    return date("%d/%m/%Y", ts)
end

local function CreatePanel(parent)
    local panel = CreateFrame("Frame", nil, parent, "BackdropTemplate")
    panel:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8X8",
        edgeFile = "Interface\\Buttons\\WHITE8X8",
        edgeSize = 1,
    })
    panel:SetBackdropColor(0.035, 0.055, 0.085, 0.96)
    panel:SetBackdropBorderColor(0.55, 0.12, 0.85, 0.95)
    return panel
end

local function CreateButton(parent, text)
    local btn = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    btn:SetText(text)
    btn:SetSize(110, 24)
    return btn
end

local function GetNews()
    return ns.News or {}
end

function ns.GetAvailableCategories()
    local map = { ["Todas"] = true }
    local list = { "Todas" }

    for _, item in ipairs(GetNews()) do
        for _, category in ipairs(item.categories or {}) do
            if category and category ~= "" and not map[category] then
                map[category] = true
                table.insert(list, category)
            end
        end
    end

    table.sort(list, function(a, b)
        if a == "Todas" then return true end
        if b == "Todas" then return false end
        return a < b
    end)

    return list
end

local function MatchesCategory(item, category)
    if not category or category == "Todas" then return true end

    for _, itemCategory in ipairs(item.categories or {}) do
        if itemCategory == category then
            return true
        end
    end

    return false
end

local function MatchesSearch(item, query)
    if not query or query == "" then return true end
    query = string.lower(query)

    local haystack = table.concat({
        SafeText(item.title),
        SafeText(item.excerpt),
        SafeText(item.author),
        table.concat(item.categories or {}, " "),
    }, " ")

    return string.find(string.lower(haystack), query, 1, true) ~= nil
end

local function InitCategoryDropdown(frame)
    UIDropDownMenu_Initialize(frame.categoryFilter, function(_, level)
        for _, category in ipairs(ns.GetAvailableCategories()) do
            local info = UIDropDownMenu_CreateInfo()
            info.text = category
            info.checked = frame.selectedCategory == category
            info.func = function()
                frame.selectedCategory = category
                UIDropDownMenu_SetText(frame.categoryFilter, category)
                ns.RenderList()
            end
            UIDropDownMenu_AddButton(info, level)
        end
    end)
end

local function EnsureFrame()
    if ns.MainFrame then return ns.MainFrame end

    local frame = CreateFrame("Frame", "AlterTimeNewsFrame", UIParent, "BackdropTemplate")
    frame:SetSize(WIDTH, HEIGHT)
    frame:SetPoint("CENTER")
    frame:SetMovable(true)
    frame:EnableMouse(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    frame:SetClampedToScreen(true)

    frame:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8X8",
        edgeFile = "Interface\\Buttons\\WHITE8X8",
        edgeSize = 1,
    })
    frame:SetBackdropColor(0.025, 0.04, 0.065, 0.98)
    frame:SetBackdropBorderColor(0.55, 0.12, 0.85, 1)

    local title = CreateFont(frame, 24, "OUTLINE")
    title:SetPoint("TOPLEFT", 18, -18)
    title:SetText("AlterTime News")
    frame.title = title

    local count = CreateFont(frame, 12)
    count:SetPoint("LEFT", title, "RIGHT", 18, -2)
    frame.count = count

    local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
    close:SetPoint("TOPRIGHT", -6, -6)

    local categoryFilter = CreateFrame("Frame", nil, frame, "UIDropDownMenuTemplate")
    categoryFilter:SetPoint("TOPLEFT", 18, -46)
    frame.categoryFilter = categoryFilter
    frame.selectedCategory = "Todas"
    UIDropDownMenu_SetWidth(categoryFilter, 160)
    UIDropDownMenu_SetText(categoryFilter, "Todas")

    local search = CreateFrame("EditBox", nil, frame, "InputBoxTemplate")
    search:SetSize(300, 24)
    search:SetPoint("TOPLEFT", 230, -48)
    search:SetAutoFocus(false)
    search:SetScript("OnTextChanged", function()
        if ns.RenderList then
            ns.RenderList()
        end
    end)
    frame.search = search

    local searchLabel = CreateFont(frame, 11)
    searchLabel:SetPoint("RIGHT", search, "LEFT", -8, 0)
    searchLabel:SetText("Buscar:")
    frame.searchLabel = searchLabel

    local back = CreateButton(frame, "Volver")
    back:SetPoint("TOPLEFT", 18, -86)
    back:SetScript("OnClick", function()
        ns.RenderList()
    end)
    frame.back = back

    local scroll = CreateFrame("ScrollFrame", nil, frame, "UIPanelScrollFrameTemplate")
    scroll:SetPoint("TOPLEFT", 18, -118)
    scroll:SetPoint("BOTTOMRIGHT", -38, 18)

    local content = CreateFrame("Frame", nil, scroll)
    content:SetSize(WIDTH - 74, 1)
    content.children = {}
    scroll:SetScrollChild(content)

    frame.scroll = scroll
    frame.content = content

    InitCategoryDropdown(frame)

    ns.MainFrame = frame
    return frame
end

function ns.RenderList()
    local frame = EnsureFrame()

    frame.back:Hide()
    frame.search:Show()
    frame.searchLabel:Show()
    frame.categoryFilter:Show()

    ClearChildren(frame.content)

    local news = GetNews()
    local y = 0
    local shown = 0
    local query = frame.search:GetText()
    local category = frame.selectedCategory or "Todas"

    UIDropDownMenu_SetText(frame.categoryFilter, category)

    for _, item in ipairs(news) do
        if MatchesSearch(item, query) and MatchesCategory(item, category) then
            shown = shown + 1

            local card = CreatePanel(frame.content)
            card:SetPoint("TOPLEFT", 0, -y)
            card:SetSize(WIDTH - 92, CARD_HEIGHT)
            AddChild(frame.content, card)

            local imageBox = CreateFrame("Frame", nil, card)
            imageBox:SetPoint("TOPLEFT", 12, -12)
            imageBox:SetSize(300, CARD_HEIGHT - 24)

            local tex = imageBox:CreateTexture(nil, "ARTWORK")
            tex:SetAllPoints(imageBox)
            tex:SetTexCoord(0, 1, 0, 1)
            tex:SetTexture(item.cover or LOGO_PATH)

            local title = CreateFont(card, 20, "OUTLINE")
            title:SetPoint("TOPLEFT", 330, -20)
            title:SetPoint("RIGHT", -18, 0)
            title:SetText(SafeText(item.title))

            local excerpt = CreateFont(card, 13)
            excerpt:SetPoint("TOPLEFT", title, "BOTTOMLEFT", 0, -12)
            excerpt:SetPoint("RIGHT", -18, 0)
            excerpt:SetText(SafeText(item.excerpt))

            local meta = CreateFont(card, 11)
            meta:SetPoint("BOTTOMRIGHT", -18, 18)
            meta:SetText(table.concat({
                SafeText(item.author),
                FormatDate(item.publishedAt),
                table.concat(item.categories or {}, ", "),
            }, "  •  "))

            local badge = CreateFont(card, 11, "OUTLINE")
            badge:SetPoint("BOTTOMLEFT", 330, 18)
            badge:SetText(ns.IsSeen(item.id) and "|cffaaaaaaVISTA|r" or "|cffd36cffNUEVA|r")

            card:SetScript("OnMouseUp", function()
                ns.MarkSeen(item.id)
                ns.RenderArticle(item)
            end)

            y = y + CARD_HEIGHT + 14
        end
    end

    frame.count:SetText(shown .. "/" .. #news .. " noticias")
    frame.content:SetHeight(math.max(y, 1))
    frame.scroll:SetVerticalScroll(0)
end

local function AddTextBlock(parent, y, blockType, text)
    local size = 14
    local flags = ""

    if blockType == "heading" then
        size = 21
        flags = "OUTLINE"
    elseif blockType == "bullet" then
        text = "• " .. SafeText(text)
    end

    local fs = CreateFont(parent, size, flags)
    fs:SetPoint("TOPLEFT", 18, -y)
    fs:SetWidth(WIDTH - 130)
    fs:SetText(SafeText(text))
    AddChild(parent, fs)

    return y + math.max(fs:GetStringHeight(), size + 8) + 14
end

local function AddImageBlock(parent, y, block)
    local path = block.path
    if not path or path == "" then return y end

    local maxWidth = WIDTH - 150
    local sourceWidth = tonumber(block.width) or maxWidth
    local sourceHeight = tonumber(block.height) or 360

    if sourceWidth <= 0 then sourceWidth = maxWidth end
    if sourceHeight <= 0 then sourceHeight = 360 end

    local ratio = sourceHeight / sourceWidth
    local displayWidth = math.min(maxWidth, sourceWidth)
    local displayHeight = math.floor(displayWidth * ratio)
    displayHeight = math.min(displayHeight, 460)

    local holder = CreateFrame("Frame", nil, parent)
    holder:SetPoint("TOPLEFT", 18, -y)
    holder:SetSize(displayWidth, displayHeight)
    AddChild(parent, holder)

    local tex = holder:CreateTexture(nil, "ARTWORK")
    tex:SetAllPoints(holder)
    tex:SetTexture(path)
    tex:SetTexCoord(0, 1, 0, 1)

    return y + displayHeight + 20
end

function ns.RenderArticle(item)
    local frame = EnsureFrame()

    frame.back:Show()
    frame.search:Hide()
    frame.searchLabel:Hide()
    frame.categoryFilter:Hide()

    ClearChildren(frame.content)

    frame.count:SetText(#GetNews() .. " noticias")

    local y = 0

    local title = CreateFont(frame.content, 25, "OUTLINE")
    title:SetPoint("TOPLEFT", 18, -y)
    title:SetWidth(WIDTH - 130)
    title:SetText(SafeText(item.title))
    AddChild(frame.content, title)
    y = y + math.max(title:GetStringHeight(), 34) + 16

    local meta = CreateFont(frame.content, 12)
    meta:SetPoint("TOPLEFT", 18, -y)
    meta:SetWidth(WIDTH - 130)
    meta:SetText(table.concat({
        SafeText(item.author),
        FormatDate(item.publishedAt),
        table.concat(item.categories or {}, ", "),
    }, "  •  "))
    AddChild(frame.content, meta)
    y = y + 30

    if item.cover then
        y = AddImageBlock(frame.content, y, {
            path = item.cover,
            width = 768,
            height = 432,
        })
    end

    for _, block in ipairs(item.body or {}) do
        if block.type == "image" then
            y = AddImageBlock(frame.content, y, block)
        else
            y = AddTextBlock(frame.content, y, block.type, block.text)
        end
    end

    y = y + 20

    local linkLabel = CreateFont(frame.content, 13, "OUTLINE")
    linkLabel:SetPoint("TOPLEFT", 18, -y)
    linkLabel:SetText("Enlace original:")
    AddChild(frame.content, linkLabel)
    y = y + 24

    local edit = CreateFrame("EditBox", nil, frame.content, "InputBoxTemplate")
    edit:SetPoint("TOPLEFT", 18, -y)
    edit:SetSize(WIDTH - 170, 24)
    edit:SetAutoFocus(false)
    edit:SetText(SafeText(item.url))
    AddChild(frame.content, edit)

    local copy = CreateButton(frame.content, "Copiar")
    copy:SetPoint("LEFT", edit, "RIGHT", 8, 0)
    copy:SetScript("OnClick", function()
        edit:HighlightText()
        edit:SetFocus()
    end)
    AddChild(frame.content, copy)

    y = y + 44

    frame.content:SetHeight(math.max(y, HEIGHT - 150))
    frame.scroll:SetVerticalScroll(0)
end

function ns.ShowMainFrame()
    local frame = EnsureFrame()
    frame:Show()
    ns.RenderList()
end
