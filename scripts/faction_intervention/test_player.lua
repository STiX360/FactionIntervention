local self = require('openmw.self')
local types = require('openmw.types')
local storage = require('openmw.storage')
local ui = require('openmw.ui')
local I = require('openmw.interfaces')
local core = require('openmw.core')
local policy = require('scripts.faction_intervention.policy')
local pendingRank

local function ready()
    types.NPC.stats.skills.mysticism(self).base = 100
    types.NPC.stats.attributes.willpower(self).base = 100
    types.NPC.stats.attributes.luck(self).base = 100
    types.Actor.stats.dynamic.magicka(self).base = 500
    types.Actor.stats.dynamic.magicka(self).current = 500
    types.Actor.stats.dynamic.fatigue(self).current = types.Actor.stats.dynamic.fatigue(self).base
end

local function status()
    local state = I.FactionIntervention.getState()
    local parts = { 'FI test: ' .. tostring(self.cell.name) .. ' ' .. tostring(self.position) }
    for _, kind in ipairs({ 'divine', 'almsivi' }) do
        local rank = types.NPC.getFactionRank(self, policy.factions[kind].id)
        parts[#parts + 1] = kind .. ': rank=' .. rank .. ', used=' .. state.used[kind]
            .. ', remaining=' .. I.FactionIntervention.getRemaining(kind)
            .. ', recoveryHours=' .. (state.recovery[kind] and
                string.format('%.2f', math.max(0, 72 - (core.getGameTime() - state.recovery[kind]) / 3600)) or 'off')
    end
    local message = table.concat(parts, '; ')
    print(message)
    ui.showMessage(message)
    return message
end

local function run(command)
    if command == 'ready' then ready()
    elseif command == 'fail' then types.Actor.stats.dynamic.magicka(self).current = 0
    elseif command == 'nonmember' then
        pendingRank = nil
        for _, faction in pairs(policy.factions) do types.NPC.leaveFaction(self, faction.id) end
    elseif command == 'member' or command == 'promote' or command == 'demote' then
        for _, faction in pairs(policy.factions) do
            types.NPC.joinFaction(self, faction.id)
        end
        pendingRank = command == 'promote' and 3 or 1
    elseif command == 'home' or command == 'day' or command == 'three-days' or command == 'diagnostics'
        or command == 'disease' or command == 'blight' then
        core.sendGlobalEvent('FactionInterventionTestAction', { player = self.object, command = command })
    elseif command ~= 'status' then error('Unknown FI test command: ' .. tostring(command)) end
    -- API stat/rank writes are delayed; inspect status after closing the console for a frame.
end

return {
    interfaceName = 'FactionInterventionTest',
    interface = { run = run, status = status },
    engineHandlers = {
        onFrame = function()
            if not pendingRank then return end
            for _, faction in pairs(policy.factions) do
                if types.NPC.getFactionRank(self, faction.id) == 0 then return end
            end
            for _, faction in pairs(policy.factions) do
                types.NPC.setFactionRank(self, faction.id, pendingRank)
            end
            pendingRank = nil
        end,
    },
    eventHandlers = {
        FactionInterventionFixtureReady = function()
            local settings = storage.playerSection('SettingsPlayerFactionIntervention')
            settings:set('enabled', true)
            settings:set('messages', true)
            for _, kind in ipairs({ 'divine', 'almsivi' }) do
                settings:set(kind .. 'Rank1', 1)
                settings:set(kind .. 'Rank3', 2)
            end
            ready()
            ui.showMessage('FI shrine test ready: two labelled shrines nearby, 500 gold, spells and items supplied.')
        end,
        FactionInterventionTestMessage = function(data) ui.showMessage(data.message) end,
    },
}
