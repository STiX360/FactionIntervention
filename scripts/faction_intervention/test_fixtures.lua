local core = require('openmw.core')
local world = require('openmw.world')
local types = require('openmw.types')
local util = require('openmw.util')
local policy = require('scripts.faction_intervention.policy')
local done = false
local home

local function itemForEffect(itemType, effectId, enchantmentType)
    local found
    for _, record in ipairs(itemType.records) do
        local enchantment = record.enchant and core.magic.enchantments.records[record.enchant]
        if enchantment and enchantment.type == enchantmentType then
            for _, effect in ipairs(enchantment.effects) do
                if effect.id == effectId and (not found or record.id < found.id) then
                    found = record
                end
            end
        end
    end
    assert(found, 'Faction Intervention test: missing item for ' .. effectId)
    return found
end

local function fixtures(player)
    if done then return end
    local kit = {}
    for _, kind in ipairs({ 'divine', 'almsivi' }) do
        local scroll = itemForEffect(types.Book, policy.effects[kind], core.magic.ENCHANTMENT_TYPE.CastOnce)
        local item = itemForEffect(types.Clothing, policy.effects[kind], core.magic.ENCHANTMENT_TYPE.CastOnUse)
        kit[#kit + 1] = scroll.id
        kit[#kit + 1] = item.id
    end
    for _, spellId in ipairs({ 'divine intervention', 'almsivi intervention', 'mark', 'recall' }) do
        assert(core.magic.spells.records[spellId], 'Faction Intervention test: missing spell ' .. spellId)
    end
    for _, spellId in ipairs({ 'divine intervention', 'almsivi intervention', 'mark', 'recall' }) do
        types.Actor.spells(player):add(spellId)
    end
    for index, recordId in ipairs(kit) do
        world.createObject(recordId, index % 2 == 1 and 10 or 1):moveInto(player)
        print('Faction Intervention fixture item: ' .. recordId)
    end
    world.createObject('gold_001', 500):moveInto(player)
    home = { cell = player.cell.name, x = player.position.x,
        y = player.position.y, z = player.position.z }
    for index, entry in ipairs({ { 'furn_imp_altar_cure_01', 'FI: Imperial altar (Divine)' },
        { 'furn_shrine_tribunal_cure_01', 'FI: Tribunal shrine (ALMSIVI)' } }) do
        local record = world.createRecord(types.Activator.createRecordDraft {
            template = types.Activator.record(entry[1]), name = entry[2],
        })
        local shrine = world.createObject(record.id)
        shrine:teleport(player.cell, player.position + util.vector3((index * 2 - 3) * 220, 260, 0),
            { onGround = true })
    end
    for _, faction in pairs(policy.factions) do types.NPC.leaveFaction(player, faction.id) end
    done = true
    player:sendEvent('FactionInterventionFixtureReady', {})
end

return {
    engineHandlers = {
        onPlayerAdded = fixtures,
        onSave = function() return { done = done, home = home } end,
        onLoad = function(data)
            -- Missing data from an older failed save must not repeat destructive setup.
            done = data == nil or data == true or (type(data) == 'table' and data.done == true)
            home = type(data) == 'table' and data.home or nil
        end,
    },
    eventHandlers = {
        FactionInterventionTestAction = function(data)
            local player = data.player
            if not player or player.type ~= types.Player then return end
            if data.command == 'home' and home then
                player:teleport(home.cell, util.vector3(home.x, home.y, home.z), { onGround = true })
            elseif data.command == 'day' then world.advanceTime(24)
            elseif data.command == 'three-days' then world.advanceTime(72)
            elseif data.command == 'disease' or data.command == 'blight' then
                local spellType = data.command == 'disease' and core.magic.SPELL_TYPE.Disease or core.magic.SPELL_TYPE.Blight
                local selected
                for _, spell in ipairs(core.magic.spells.records) do
                    if spell.type == spellType and (not selected or spell.id < selected.id) then selected = spell end
                end
                assert(selected, 'FI test: missing disease fixture')
                types.Actor.spells(player):add(selected.id)
                print('FI test affliction: ' .. selected.id)
                player:sendEvent('FactionInterventionTestMessage', { message = 'FI test affliction: ' .. selected.name })
            elseif data.command == 'diagnostics' then
                local counts = require('openmw.interfaces').FactionInterventionShrines.getDiagnostics()
                local parts = {}
                for _, key in ipairs({ 'started', 'confirmed', 'cancelled', 'noEffect', 'expired' }) do
                    parts[#parts + 1] = key .. '=' .. counts[key]
                end
                print('FI shrine diagnostics: ' .. table.concat(parts, ', '))
                player:sendEvent('FactionInterventionTestMessage', { message = table.concat(parts, ', ') })
            end
        end,
    },
}
