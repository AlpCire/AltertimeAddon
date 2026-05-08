local ADDON_NAME, ns = ...

ns.ADDON_NAME = ADDON_NAME
ns.VERSION = "0.3.2-alpha"
ns.DATA_VERSION = 1

local DEFAULT_DB = {
    version = 2,
    seen = {},
    settings = {
        scale = 1,
        debug = false,
        selectedCategory = "Todas",
        search = "",
    },
}

local function CopyDefaults(src, dst)
    if type(dst) ~= "table" then dst = {} end
    for k, v in pairs(src) do
        if type(v) == "table" then
            dst[k] = CopyDefaults(v, dst[k])
        elseif dst[k] == nil then
            dst[k] = v
        end
    end
    return dst
end

local function PruneInvalidSeen(db)
    if type(db.seen) ~= "table" then db.seen = {} return end
    local valid = {}
    for _, news in ipairs(ns.News or {}) do
        if news.id then valid[news.id] = true end
    end
    for id in pairs(db.seen) do
        if not valid[id] then db.seen[id] = nil end
    end
end

function ns.GetDB()
    AlterTimeNewsDB = CopyDefaults(DEFAULT_DB, AlterTimeNewsDB)
    if type(AlterTimeNewsDB.seen) ~= "table" then AlterTimeNewsDB.seen = {} end
    if type(AlterTimeNewsDB.settings) ~= "table" then AlterTimeNewsDB.settings = {} end
    AlterTimeNewsDB.version = DEFAULT_DB.version
    return AlterTimeNewsDB
end

function ns.Debug(...)
    local db = ns.GetDB()
    if not db.settings.debug then return end
    print("|cff8e44adAlterTime|r", ...)
end

function ns.SafeCall(fn, ...)
    if type(fn) ~= "function" then return nil end
    local ok, result = pcall(fn, ...)
    if not ok then
        ns.Debug("Error:", result)
        return nil
    end
    return result
end

function ns.MarkSeen(id)
    local db = ns.GetDB()
    if id then db.seen[id] = time() end
end

function ns.IsSeen(id)
    local db = ns.GetDB()
    return id and db.seen[id] ~= nil
end

function ns.FormatDate(ts)
    if type(ts) ~= "number" or ts <= 0 then return "Fecha desconocida" end
    return date("%d/%m/%Y", ts)
end

function ns.NormalizeText(value)
    if type(value) ~= "string" then return "" end
    value = value:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")
    return value:lower()
end

function ns.NewsMatches(news, category, search)
    if type(news) ~= "table" then return false end

    if category and category ~= "" and category ~= "Todas" then
        local found = false
        for _, c in ipairs(news.categories or {}) do
            if c == category then found = true break end
        end
        if not found then return false end
    end

    search = ns.NormalizeText(search)
    if search ~= "" then
        local haystack = ns.NormalizeText((news.title or "") .. " " .. (news.excerpt or "") .. " " .. (news.author or ""))
        if not haystack:find(search, 1, true) then return false end
    end

    return true
end

function ns.GetCategories()
    local seen, categories = { Todas = true }, { "Todas" }
    for _, news in ipairs(ns.News or {}) do
        for _, category in ipairs(news.categories or {}) do
            if not seen[category] then
                seen[category] = true
                table.insert(categories, category)
            end
        end
    end
    table.sort(categories, function(a, b)
        if a == "Todas" then return true end
        if b == "Todas" then return false end
        return a < b
    end)
    return categories
end

function ns.GetFilteredNews()
    local db = ns.GetDB()
    local output = {}
    for _, news in ipairs(ns.News or {}) do
        if ns.NewsMatches(news, db.settings.selectedCategory, db.settings.search) then
            table.insert(output, news)
        end
    end
    table.sort(output, function(a, b)
        return (a.publishedAt or 0) > (b.publishedAt or 0)
    end)
    return output
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("ADDON_LOADED")
frame:SetScript("OnEvent", function(_, event, addonName)
    if event ~= "ADDON_LOADED" or addonName ~= ADDON_NAME then return end

    local db = ns.GetDB()
    PruneInvalidSeen(db)

    SLASH_ALTERTIMENEWS1 = "/altertime"
    SLASH_ALTERTIMENEWS2 = "/atnews"
    SlashCmdList.ALTERTIMENEWS = function(msg)
        msg = msg and msg:lower() or ""
        if msg == "debug" then
            db.settings.debug = not db.settings.debug
            print("|cff8e44adAlterTime News|r debug:", db.settings.debug and "ON" or "OFF")
            return
        end
        if ns.ToggleMainFrame then
            ns.ToggleMainFrame()
        else
            print("|cff8e44adAlterTime|r UI no disponible.")
        end
    end

    print("|cff8e44adAlterTime News|r cargado. Usa /altertime")
end)
