local core = require('openmw.core')
local types = require('openmw.types')
local world = require('openmw.world')
local I = require('openmw.interfaces')
local policy = require('scripts.faction_intervention.shrine_policy')
local pending = {}
local counts = { started = 0, confirmed = 0, cancelled = 0, expired = 0, noEffect = 0 }

local function baseline(actor)
    local seen = {}
    for _, spell in pairs(types.Actor.activeSpells(actor)) do
        if spell.activeSpellId then seen[spell.activeSpellId] = true end
    end
    return seen
end

local function activated(object, actor)
    if actor.type ~= types.Player then return end
    -- Activating another activator ends the previous shrine interaction.
    pending[actor.id] = nil
    if object.type ~= types.Activator then return end
    local config = policy.config(types.Activator.record(object).mwscript)
    if not config then return end
    local session = policy.start(config, baseline(actor), core.getSimulationTime())
    session.object = object
    session.actor = actor
    pending[actor.id] = session
    counts.started = counts.started + 1
    print('FI shrine interaction started: ' .. object.recordId .. ' (' .. config.kind .. ')')
end

local function update()
    for id, session in pairs(pending) do
        local object, actor = session.object, session.actor
        if not object:isValid() or not actor:isValid() or object.cell ~= actor.cell then
            pending[id] = nil
        else
            for _, spell in pairs(types.Actor.activeSpells(actor)) do policy.observe(session, spell) end
            local script = world.mwscript.getLocalScript(object, actor)
            if script then
                local result = policy.step(session, script.variables.questionstate, script.variables.button,
                    core.getSimulationTime())
                if result then
                    counts[result] = counts[result] + 1
                    print('FI shrine interaction ' .. result .. ': ' .. object.recordId
                        .. ', service=' .. tostring(session.button))
                    if result == 'confirmed' then
                        actor:sendEvent('FactionInterventionShrineCompleted', { kind = session.config.kind })
                    end
                    pending[id] = nil
                end
            elseif core.getSimulationTime() > session.expires then
                pending[id] = nil
                counts.expired = counts.expired + 1
            end
        end
    end
end

-- Observe activation without consuming it; the normal MWScript menu still runs.
I.Activation.addHandlerForType(types.Activator, activated)

return {
    interfaceName = 'FactionInterventionShrines',
    interface = {
        getDiagnostics = function()
            local copy = {}
            for key, value in pairs(counts) do copy[key] = value end
            return copy
        end,
    },
    engineHandlers = {
        onUpdate = update,
        onLoad = function() pending = {} end,
        onSave = function() pending = {}; return nil end,
    },
}
