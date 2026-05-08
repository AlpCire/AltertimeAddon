local ADDON_NAME, ns = ...

function ns.RGB(hex)
    hex = (hex or "#ffffff"):gsub("#", "")
    return tonumber(hex:sub(1,2),16)/255, tonumber(hex:sub(3,4),16)/255, tonumber(hex:sub(5,6),16)/255
end

function ns.SetBackdrop(frame, bg, border)
    if not frame.SetBackdrop then
        Mixin(frame, BackdropTemplateMixin)
    end
    frame:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    frame:SetBackdropColor(ns.RGB(bg or "#111722"))
    frame:SetBackdropBorderColor(ns.RGB(border or "#8e44ad"))
end

function ns.WipeChildren(frame)
    local children = { frame:GetChildren() }
    for _, child in ipairs(children) do
        child:Hide()
        child:SetParent(nil)
    end
end

function ns.CategoriesToText(categories)
    if type(categories) ~= "table" then return "" end
    return table.concat(categories, ", ")
end

function ns.CreateFont(parent, size, flags, template)
    local fs = parent:CreateFontString(nil, "OVERLAY", template or "GameFontNormal")
    fs:SetFont(STANDARD_TEXT_FONT, size, flags or "")
    fs:SetTextColor(0.92, 0.94, 0.98)
    fs:SetJustifyH("LEFT")
    fs:SetJustifyV("TOP")
    return fs
end

function ns.CreateCopyBox(parent, text)
    local edit = CreateFrame("EditBox", nil, parent, "InputBoxTemplate")
    edit:SetAutoFocus(false)
    edit:SetText(text or "")
    edit:SetCursorPosition(0)
    edit:SetHeight(26)
    edit:SetFontObject(ChatFontNormal)
    edit:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    edit:SetScript("OnEditFocusGained", function(self) self:HighlightText() end)
    return edit
end
