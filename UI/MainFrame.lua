local ADDON_NAME, ns = ...

local MAIN_WIDTH, MAIN_HEIGHT = 1040, 680
local CARD_HEIGHT = 142

local mainFrame
local listFrame
local articleFrame
local searchBox
local categoryDropDown
local resultText

local function ShowList()
    articleFrame:Hide()
    listFrame:Show()
end

local function AddVerticalSpace(y, amount)
    return y - (amount or 12)
end

local function ShowArticle(news)
    if type(news) ~= "table" then return end

    ns.MarkSeen(news.id)

    listFrame:Hide()
    articleFrame:Show()
    ns.WipeChildren(articleFrame.content)

    local y = -8

    local back = CreateFrame("Button", nil, articleFrame.content, "UIPanelButtonTemplate")
    back:SetText("← Volver")
    back:SetSize(110, 26)
    back:SetPoint("TOPLEFT", 8, y)
    back:SetScript("OnClick", function()
        BuildList()
        ShowList()
    end)
    y = AddVerticalSpace(y, 42)

    local title = ns.CreateFont(articleFrame.content, 24, "OUTLINE")
    title:SetPoint("TOPLEFT", 8, y)
    title:SetPoint("RIGHT", articleFrame.content, "RIGHT", -24, 0)
    title:SetText(news.title or "Sin título")
    title:SetWordWrap(true)
    y = AddVerticalSpace(y, math.max(64, title:GetStringHeight() + 18))

    local meta = ns.CreateFont(articleFrame.content, 12)
    meta:SetTextColor(0.72, 0.76, 0.84)
    meta:SetPoint("TOPLEFT", 8, y)
    meta:SetText((news.author or "AlterTime") .. "  •  " .. ns.FormatDate(news.publishedAt) .. "  •  " .. ns.CategoriesToText(news.categories))
    y = AddVerticalSpace(y, 34)

    if news.cover then
        local cover = articleFrame.content:CreateTexture(nil, "ARTWORK")
        cover:SetTexture(news.cover)
        cover:SetSize(760, 300)
        cover:SetPoint("TOP", articleFrame.content, "TOP", 0, y)
        cover:SetTexCoord(0, 1, 0, 1)
        y = AddVerticalSpace(y, 320)
    end

    for _, block in ipairs(news.body or {}) do
        if block.type == "heading" then
            local h = ns.CreateFont(articleFrame.content, 20, "OUTLINE")
            h:SetPoint("TOPLEFT", 8, y)
            h:SetPoint("RIGHT", articleFrame.content, "RIGHT", -24, 0)
            h:SetText(block.text or "")
            y = AddVerticalSpace(y, math.max(34, h:GetStringHeight() + 14))
        elseif block.type == "bullet" then
            local b = ns.CreateFont(articleFrame.content, 15)
            b:SetPoint("TOPLEFT", 28, y)
            b:SetPoint("RIGHT", articleFrame.content, "RIGHT", -24, 0)
            b:SetText("• " .. (block.text or ""))
            b:SetWordWrap(true)
            y = AddVerticalSpace(y, math.max(28, b:GetStringHeight() + 12))
        elseif block.type == "image" and block.path then
            local tex = articleFrame.content:CreateTexture(nil, "ARTWORK")
            tex:SetTexture(block.path)
            tex:SetSize(block.width or 720, block.height or 360)
            tex:SetPoint("TOP", articleFrame.content, "TOP", 0, y)
            y = AddVerticalSpace(y, (block.height or 360) + 20)
        else
            local p = ns.CreateFont(articleFrame.content, 15)
            p:SetPoint("TOPLEFT", 8, y)
            p:SetPoint("RIGHT", articleFrame.content, "RIGHT", -24, 0)
            p:SetText(block.text or "")
            p:SetWordWrap(true)
            y = AddVerticalSpace(y, math.max(32, p:GetStringHeight() + 16))
        end
    end

    local linkLabel = ns.CreateFont(articleFrame.content, 14, "OUTLINE")
    linkLabel:SetPoint("TOPLEFT", 8, y - 10)
    linkLabel:SetText("Enlace original:")
    y = AddVerticalSpace(y, 38)

    local edit = ns.CreateCopyBox(articleFrame.content, news.url or "")
    edit:SetPoint("TOPLEFT", 8, y)
    edit:SetPoint("RIGHT", articleFrame.content, "RIGHT", -88, 0)

    local copy = CreateFrame("Button", nil, articleFrame.content, "UIPanelButtonTemplate")
    copy:SetText("Copiar")
    copy:SetSize(76, 24)
    copy:SetPoint("LEFT", edit, "RIGHT", 8, 0)
    copy:SetScript("OnClick", function()
        edit:SetFocus()
        edit:HighlightText()
    end)

    y = AddVerticalSpace(y, 56)
    articleFrame.content:SetHeight(math.abs(y) + 40)
end

function BuildList()
    if not listFrame or not listFrame.content then return end
    ns.WipeChildren(listFrame.content)

    local news = ns.GetFilteredNews()
    if resultText then
        resultText:SetText(string.format("%d noticia%s", #news, #news == 1 and "" or "s"))
    end

    if #news == 0 then
        local empty = ns.CreateFont(listFrame.content, 16)
        empty:SetPoint("TOPLEFT", 16, -18)
        empty:SetText("No hay noticias para el filtro actual.")
        listFrame.content:SetHeight(80)
        return
    end

    for i, item in ipairs(news) do
        local card = CreateFrame("Button", nil, listFrame.content, "BackdropTemplate")
        card:SetSize(MAIN_WIDTH - 92, CARD_HEIGHT)
        card:SetPoint("TOPLEFT", 12, -12 - ((i - 1) * (CARD_HEIGHT + 14)))
        ns.SetBackdrop(card, "#151b24", ns.IsSeen(item.id) and "#3d4655" or "#7c2bbd")

        local cover = card:CreateTexture(nil, "ARTWORK")
        cover:SetPoint("TOPLEFT", 1, -1)
        cover:SetPoint("BOTTOMLEFT", 1, 1)
        cover:SetWidth(330)
        cover:SetTexture(item.cover or "Interface\\Collections\\CollectionsBackgroundTile")
        cover:SetAlpha(item.cover and 0.8 or 0.35)

        local title = ns.CreateFont(card, 21, "OUTLINE")
        title:SetPoint("TOPLEFT", card, "TOPLEFT", 360, -22)
        title:SetPoint("RIGHT", card, "RIGHT", -18, 0)
        title:SetText(item.title or "Sin título")
        title:SetWordWrap(true)

        local excerpt = ns.CreateFont(card, 14)
        excerpt:SetTextColor(0.82, 0.84, 0.90)
        excerpt:SetPoint("TOPLEFT", title, "BOTTOMLEFT", 0, -10)
        excerpt:SetPoint("RIGHT", card, "RIGHT", -18, 0)
        excerpt:SetText(item.excerpt or "")

        local badge = ns.CreateFont(card, 12, "OUTLINE")
        badge:SetPoint("BOTTOMLEFT", card, "BOTTOMLEFT", 360, 18)
        badge:SetText(ns.IsSeen(item.id) and "VISTA" or "NUEVA")
        badge:SetTextColor(ns.IsSeen(item.id) and 0.55 or 0.80, ns.IsSeen(item.id) and 0.62 or 0.45, ns.IsSeen(item.id) and 0.72 or 1.0)

        local meta = ns.CreateFont(card, 12)
        meta:SetTextColor(0.78, 0.80, 0.86)
        meta:SetPoint("BOTTOMRIGHT", card, "BOTTOMRIGHT", -18, 18)
        meta:SetJustifyH("RIGHT")
        meta:SetText((item.author or "AlterTime") .. "  •  " .. ns.FormatDate(item.publishedAt) .. "  •  " .. ns.CategoriesToText(item.categories))

        card:SetScript("OnEnter", function(self) self:SetBackdropBorderColor(ns.RGB("#b85cff")) end)
        card:SetScript("OnLeave", function(self) self:SetBackdropBorderColor(ns.RGB(ns.IsSeen(item.id) and "#3d4655" or "#7c2bbd")) end)
        card:SetScript("OnClick", function() ShowArticle(item) end)
    end

    listFrame.content:SetHeight(math.max(1, (#news * (CARD_HEIGHT + 14)) + 30))
end

local function CreateScroll(parent)
    local scroll = CreateFrame("ScrollFrame", nil, parent, "UIPanelScrollFrameTemplate")
    scroll:SetPoint("TOPLEFT", 16, -92)
    scroll:SetPoint("BOTTOMRIGHT", -36, 18)

    local content = CreateFrame("Frame", nil, scroll)
    content:SetSize(1, 1)
    scroll:SetScrollChild(content)
    scroll.content = content
    return scroll
end

local function RebuildFilters()
    local db = ns.GetDB()
    if searchBox then
        db.settings.search = searchBox:GetText() or ""
    end
    BuildList()
end

local function CreateCategoryDropdown(parent)
    local dropdown = CreateFrame("Frame", "AlterTimeNewsCategoryDropDown", parent, "UIDropDownMenuTemplate")
    UIDropDownMenu_SetWidth(dropdown, 150)
    UIDropDownMenu_Initialize(dropdown, function(self, level)
        local db = ns.GetDB()
        for _, category in ipairs(ns.GetCategories()) do
            local info = UIDropDownMenu_CreateInfo()
            info.text = category
            info.checked = db.settings.selectedCategory == category
            info.func = function()
                db.settings.selectedCategory = category
                UIDropDownMenu_SetText(dropdown, category)
                BuildList()
            end
            UIDropDownMenu_AddButton(info, level)
        end
    end)
    UIDropDownMenu_SetText(dropdown, ns.GetDB().settings.selectedCategory or "Todas")
    return dropdown
end

local function CreateMainFrame()
    if mainFrame then return mainFrame end

    mainFrame = CreateFrame("Frame", "AlterTimeNewsMainFrame", UIParent, "BackdropTemplate")
    mainFrame:SetSize(MAIN_WIDTH, MAIN_HEIGHT)
    mainFrame:SetPoint("CENTER")
    mainFrame:SetFrameStrata("DIALOG")
    mainFrame:EnableMouse(true)
    mainFrame:SetMovable(true)
    mainFrame:RegisterForDrag("LeftButton")
    mainFrame:SetScript("OnDragStart", mainFrame.StartMoving)
    mainFrame:SetScript("OnDragStop", mainFrame.StopMovingOrSizing)
    ns.SetBackdrop(mainFrame, "#111722", "#8e44ad")
    mainFrame:Hide()

    local title = ns.CreateFont(mainFrame, 22, "OUTLINE")
    title:SetPoint("TOPLEFT", 18, -16)
    title:SetText("AlterTime News")

    resultText = ns.CreateFont(mainFrame, 12)
    resultText:SetTextColor(0.72, 0.76, 0.84)
    resultText:SetPoint("LEFT", title, "RIGHT", 18, 0)

    categoryDropDown = CreateCategoryDropdown(mainFrame)
    categoryDropDown:SetPoint("TOPLEFT", 12, -46)

    searchBox = CreateFrame("EditBox", nil, mainFrame, "InputBoxTemplate")
    searchBox:SetSize(260, 28)
    searchBox:SetPoint("LEFT", categoryDropDown, "RIGHT", 8, 2)
    searchBox:SetAutoFocus(false)
    searchBox:SetText(ns.GetDB().settings.search or "")
    searchBox:SetScript("OnTextChanged", function(self)
        ns.GetDB().settings.search = self:GetText() or ""
        BuildList()
    end)
    searchBox:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)

    local placeholder = ns.CreateFont(mainFrame, 12)
    placeholder:SetTextColor(0.45, 0.48, 0.55)
    placeholder:SetPoint("LEFT", searchBox, "LEFT", 8, 0)
    placeholder:SetText("Buscar...")
    searchBox:SetScript("OnEditFocusGained", function() placeholder:Hide() end)
    searchBox:SetScript("OnEditFocusLost", function(self)
        if (self:GetText() or "") == "" then placeholder:Show() end
    end)
    if (searchBox:GetText() or "") ~= "" then placeholder:Hide() end

    local close = CreateFrame("Button", nil, mainFrame, "UIPanelCloseButton")
    close:SetPoint("TOPRIGHT", -4, -4)

    listFrame = CreateScroll(mainFrame)
    articleFrame = CreateScroll(mainFrame)
    articleFrame:Hide()

    BuildList()
    return mainFrame
end

function ns.ToggleMainFrame()
    local f = CreateMainFrame()
    if f:IsShown() then
        f:Hide()
    else
        BuildList()
        ShowList()
        f:Show()
    end
end
