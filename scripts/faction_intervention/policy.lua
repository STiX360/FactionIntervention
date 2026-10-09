local M = {}

M.version = 2
M.recoveryInterval = 3 * 24 * 60 * 60

M.effects = {
    divine = 'divineintervention',
    almsivi = 'almsiviintervention',
}

M.factions = {
    divine = { id = 'imperial cult', label = 'Imperial Cult' },
    almsivi = { id = 'temple', label = 'Tribunal Temple' },
}

M.defaultAllowances = {
    divine = { 1, 1, 2, 2, 3, 3, 4, 4, 5, 6 },
    almsivi = { 1, 1, 2, 2, 3, 3, 4, 4, 5, 6 },
}

local function clampNumber(value, fallback, low, high)
    if type(value) ~= 'number' or value ~= value then
        value = fallback
    end
    value = math.floor(value)
    if value < low then return low end
    if value > high then return high end
    return value
end
M.clampNumber = clampNumber

local function effectsKind(effects, core)
    local found
    for _, effect in ipairs(effects or {}) do
        if effect.id == M.effects.divine then
            found = found or 'divine'
        elseif effect.id == M.effects.almsivi then
            found = found or 'almsivi'
        elseif effect.id == core.magic.EFFECT_TYPE.Recall or effect.id == 'recall' then
            return nil
        end
    end
    return found
end

function M.spellKind(spell, core)
    if not spell or spell.type ~= core.magic.SPELL_TYPE.Spell then return nil end
    return effectsKind(spell.effects, core)
end

function M.enchantmentKind(enchantment, core)
    if not enchantment then return nil end
    local types = core.magic.ENCHANTMENT_TYPE
    if enchantment.type ~= types.CastOnce and enchantment.type ~= types.CastOnUse then return nil end
    return effectsKind(enchantment.effects, core)
end

function M.allowance(kind, rank, settings)
    rank = clampNumber(rank, 0, 0, 10)
    if rank <= 0 then return 0 end
    local key = kind .. 'Rank' .. rank
    return clampNumber(settings:get(key), M.defaultAllowances[kind][rank] or 0, 0, 99)
end

function M.remaining(kind, rank, used, settings)
    local cap = M.allowance(kind, rank, settings)
    local spent = clampNumber(used and used[kind] or 0, 0, 0, 9999)
    local left = cap - spent
    if left < 0 then return 0, cap, spent end
    return left, cap, spent
end

function M.normaliseState(data)
    data = type(data) == 'table' and data or {}
    local used = type(data.used) == 'table' and data.used or {}
    local bestRank = type(data.bestRank) == 'table' and data.bestRank or {}
    local recovery = type(data.recovery) == 'table' and data.recovery or {}
    local function timestamp(value)
        if type(value) == 'number' and value == value and value >= 0 and value < math.huge then
            return value
        end
    end
    return {
        version = M.version,
        used = {
            divine = clampNumber(used.divine, 0, 0, 9999),
            almsivi = clampNumber(used.almsivi, 0, 0, 9999),
        },
        bestRank = {
            divine = clampNumber(bestRank.divine, 0, 0, 10),
            almsivi = clampNumber(bestRank.almsivi, 0, 0, 10),
        },
        recovery = { divine = timestamp(recovery.divine), almsivi = timestamp(recovery.almsivi) },
    }
end

function M.recordSuccess(state, kind, now)
    state.used[kind] = clampNumber((state.used[kind] or 0) + 1, 0, 0, 9999)
    if not state.recovery[kind] then state.recovery[kind] = now end
end

function M.recover(state, kind, rank, settings, now)
    state.bestRank[kind] = math.max(state.bestRank[kind] or 0, rank)
    if state.used[kind] <= 0 then
        state.recovery[kind] = nil
        return 0
    end
    if not state.recovery[kind] or state.recovery[kind] > now then
        state.recovery[kind] = now
        return 0
    end
    -- No membership means no usable capacity. Pause progress rather than bank it.
    if M.allowance(kind, rank, settings) == 0 then
        state.recovery[kind] = now
        return 0
    end
    local ticks = math.floor((now - state.recovery[kind]) / M.recoveryInterval)
    local restored = math.min(ticks, state.used[kind])
    state.used[kind] = state.used[kind] - restored
    if state.used[kind] == 0 then
        state.recovery[kind] = nil
    else
        state.recovery[kind] = state.recovery[kind] + ticks * M.recoveryInterval
    end
    return restored
end

function M.refill(state, kind)
    local restored = state.used[kind]
    state.used[kind] = 0
    state.recovery[kind] = nil
    return restored
end

function M.statusMessage(kind, rank, used, settings)
    local left, cap = M.remaining(kind, rank, used, settings)
    local label = M.factions[kind].label
    if cap == 0 then
        return label .. ' grants you no remaining Intervention allowance.'
    end
    if left == 1 then
        return label .. ' Intervention allowance: 1 use remains.'
    end
    return label .. ' Intervention allowance: ' .. left .. ' uses remain.'
end

function M.refusalMessage(kind, rank, used, settings)
    local _, cap = M.remaining(kind, rank, used, settings)
    if rank <= 0 then
        return 'Intervention refused: you are not ranked in the ' .. M.factions[kind].label .. '.'
    end
    return 'Intervention refused: your ' .. M.factions[kind].label
        .. ' rank allows ' .. cap .. ' use(s), and that allowance is spent.'
end

return M
