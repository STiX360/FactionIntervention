local core = require('openmw.core')
local animation = require('openmw.animation')
local self = require('openmw.self')
local storage = require('openmw.storage')
local ui = require('openmw.ui')
local types = require('openmw.types')
local I = require('openmw.interfaces')
local policy = require('scripts.faction_intervention.policy')

local NPC = types.NPC
local Actor = types.Actor

local group = 'SettingsPlayerFactionIntervention'

I.Settings.registerPage { key = 'FactionIntervention', l10n = 'FactionIntervention', name = 'PageName' }

local generalSettingsSpec = {
    { key = 'enabled', renderer = 'checkbox', name = 'Enabled', default = true },
    { key = 'messages', renderer = 'checkbox', name = 'Messages', default = true },
    { key = 'exemptItems', renderer = 'checkbox', name = 'ExemptItems', default = true },
}

I.Settings.registerGroup {
    key = group,
    page = 'FactionIntervention',
    l10n = 'FactionIntervention',
    name = 'General',
    order = 0,
    permanentStorage = false,
    settings = generalSettingsSpec,
}

local generalSettings = storage.playerSection(group)
local settingSections = {}
local settingsSpec = {}
for _, spec in ipairs(generalSettingsSpec) do
    settingsSpec[#settingsSpec + 1] = spec
    settingSections[spec.key] = generalSettings
end

for index, kind in ipairs({ 'divine', 'almsivi' }) do
    local rankSettings = {}
    local sectionKey = group .. '_' .. kind
    local section = storage.playerSection(sectionKey)
    for rank = 1, policy.maxRank do
        local spec = {
            key = kind .. 'Rank' .. rank,
            renderer = 'number',
            name = kind .. 'Rank' .. rank,
            default = policy.defaultAllowances[kind][rank],
            argument = { min = 0, max = 99 },
        }
        rankSettings[#rankSettings + 1] = spec
        settingsSpec[#settingsSpec + 1] = spec
        settingSections[spec.key] = section
    end
    I.Settings.registerGroup {
        key = sectionKey,
        page = 'FactionIntervention',
        l10n = 'FactionIntervention',
        name = kind .. 'Allowances',
        description = kind .. 'Faction',
        order = index,
        permanentStorage = false,
        settings = rankSettings,
    }
end

-- Keep the existing flat save keys while the UI uses three storage groups.
local settings = {
    get = function(_, key) return settingSections[key]:get(key) end,
    set = function(_, key, value) settingSections[key]:set(key, value) end,
}

local state = policy.normaliseState(nil)
local saved
local pendingAllowed

local function messagesEnabled()
    return settings:get('messages') ~= false
end

local function getRank(kind)
    local ok, rank = pcall(NPC.getFactionRank, self, policy.factions[kind].id)
    if not ok then return 0 end
    return policy.clampNumber(rank, 0, 0, 10)
end

local function selectedIntervention()
    if settings:get('enabled') == false then return nil end
    if Actor.getStance(self) ~= Actor.STANCE.Spell then return nil end
    local item = Actor.getSelectedEnchantedItem(self)
    if item then
        if settings:get('exemptItems') ~= false then return nil end
        local record = item.type.record(item)
        local enchantment = record.enchant and core.magic.enchantments.records[record.enchant]
        local kind = policy.enchantmentKind(enchantment, core)
        if not kind then return nil end
        local source = enchantment.type == core.magic.ENCHANTMENT_TYPE.CastOnce and 'scroll' or 'item'
        return kind, { source = source, spellId = record.id,
            count = source == 'scroll' and Actor.inventory(self):countOf(record.id) or nil }
    end
    local spell = Actor.getSelectedSpell(self)
    local kind = policy.spellKind(spell, core)
    if not kind then return nil end
    return kind, { source = 'spell', spellId = spell.id }
end

local function updateRecovery()
    if settings:get('enabled') == false then return end
    for _, kind in ipairs({ 'divine', 'almsivi' }) do
        local restored = policy.recover(state, kind, getRank(kind), settings, core.getGameTime())
        if restored > 0 and messagesEnabled() then
            ui.showMessage(policy.factions[kind].label .. ' Intervention recovered ' .. restored .. ' use(s).')
        end
    end
end

local function blockThisFrame(kind, rank)
    pendingAllowed = nil
    self.controls.use = self.ATTACK_TYPE.NoAttack
    if messagesEnabled() then
        ui.showMessage(policy.refusalMessage(kind, rank, state.used, settings))
    end
end

local function allowThisFrame(kind, rank, cast)
    cast.kind = kind
    cast.rank = rank
    cast.started = core.getSimulationTime()
    pendingAllowed = cast
end

local function castingAnimationPlaying()
    return animation.hasAnimation(self) and animation.isPlaying(self, 'spellcast')
end

local function completePending()
    local cast = pendingAllowed
    pendingAllowed = nil
    if settings:get('enabled') == false then return end
    if cast.source ~= 'spell' and settings:get('exemptItems') ~= false then return end
    -- A successful casting roll or consumed scroll can still have its teleport blocked.
    if not types.Player.isTeleportingEnabled(self) then return end
    if policy.isUnlimited(cast.kind, cast.rank, settings)
        or policy.isUnlimited(cast.kind, getRank(cast.kind), settings) then return end
    policy.recordSuccess(state, cast.kind, core.getGameTime())
    if messagesEnabled() then
        ui.showMessage(policy.statusMessage(cast.kind, cast.rank, state.used, settings))
    end
end

local function inspectUseFrame()
    local casting = castingAnimationPlaying()
    -- Scrolls emit no skill-use event. Observe consumption before clearing a finished animation.
    if pendingAllowed and pendingAllowed.source == 'scroll'
        and (casting or pendingAllowed.sawAnimation or core.getSimulationTime() - pendingAllowed.started <= 3)
        and Actor.inventory(self):countOf(pendingAllowed.spellId) < pendingAllowed.count then
        completePending()
    end
    -- The engine ignores new cast requests during this animation; retain its original candidate.
    if casting then
        if pendingAllowed then pendingAllowed.sawAnimation = true end
        return
    end
    if pendingAllowed and (pendingAllowed.sawAnimation
        or core.getSimulationTime() - pendingAllowed.started > 3) then
        pendingAllowed = nil
    end
    if self.controls.use == self.ATTACK_TYPE.NoAttack then return end
    local kind, cast = selectedIntervention()
    if not kind then
        pendingAllowed = nil
        return
    end
    local rank = getRank(kind)
    local remaining = policy.remaining(kind, rank, state.used, settings)
    if remaining <= 0 then
        blockThisFrame(kind, rank)
    else
        allowThisFrame(kind, rank, cast)
    end
end

local function onSkillUse(skill, options)
    if not pendingAllowed then return end
    if not options then return end
    local source = pendingAllowed.source
    if source == 'spell' then
        if skill ~= 'mysticism' or options.useType ~= I.SkillProgression.SKILL_USE_TYPES.Spellcast_Success then return end
    elseif source == 'item' then
        if skill ~= 'enchant' or options.useType ~= I.SkillProgression.SKILL_USE_TYPES.Enchant_UseMagicItem then return end
    else
        return
    end
    if settings:get('enabled') == false or (not castingAnimationPlaying()
        and core.getSimulationTime() - pendingAllowed.started > 3) then
        pendingAllowed = nil
        return
    end
    completePending()
end

I.SkillProgression.addSkillUsedHandler(onSkillUse)

local function initialise()
    if saved then
        state = policy.normaliseState(saved)
        for _, spec in ipairs(settingsSpec) do
            local value = saved.settings and saved.settings[spec.key]
            if value == nil then value = spec.default end
            settings:set(spec.key, value)
        end
        saved = nil
    end
end

return {
    interfaceName = 'FactionIntervention',
    interface = {
        version = 2,
        getState = function() return policy.normaliseState(state) end,
        getRemaining = function(kind)
            local rank = getRank(kind)
            return policy.remaining(kind, rank, state.used, settings)
        end,
    },
    engineHandlers = {
        onFrame = function()
            initialise()
            updateRecovery()
            inspectUseFrame()
        end,
        onLoad = function(data)
            saved = data
            state = policy.normaliseState(data)
            pendingAllowed = nil
        end,
        onSave = function()
            initialise()
            updateRecovery()
            local data = policy.normaliseState(state)
            data.settings = {}
            for _, spec in ipairs(settingsSpec) do
                data.settings[spec.key] = settings:get(spec.key)
            end
            return data
        end,
    },
    eventHandlers = {
        FactionInterventionShrineCompleted = function(data)
            initialise()
            local kind = data.kind
            if not policy.factions[kind] or settings:get('enabled') == false or getRank(kind) == 0 then return end
            policy.refill(state, kind)
            if messagesEnabled() and not policy.isUnlimited(kind, getRank(kind), settings) then
                ui.showMessage(policy.factions[kind].label .. ' Intervention allowance fully restored by shrine service.')
            end
        end,
    },
}
