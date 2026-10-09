local M = {}

local cures = {
    [0] = { 'cure common disease other' },
    [1] = { 'cure blight disease' },
    [2] = { 'cure poison touch' },
}

M.scripts = {
    shrineimperial = {
        kind = 'divine', services = {
            [0] = cures[0], [1] = cures[1], [2] = cures[2],
            [3] = { 'restore attributes', 'restore fighter', 'restore mage', 'restore stealth', 'restore other' },
        },
    },
    shrinetemple = {
        kind = 'almsivi', services = {
            [0] = cures[0], [1] = cures[1], [2] = cures[2],
            [3] = { "lady's grace shrine" }, [4] = { 'soul of sotha sil' }, [5] = { "vivec's mystery" },
            [6] = { 'almsivi restoration', 'almsivi restore fighter', 'almsivi restore mage',
                'almsivi restore stealth', 'almsivi restore other' },
        },
    },
    shrineveloth = {
        kind = 'almsivi', services = {
            [0] = cures[0], [1] = cures[1], [2] = cures[2],
            [3] = { "veloth's indwelling" }, [4] = { 'almsivi restoration' },
        },
    },
}

for scriptId, blessing in pairs({ shrinevivecfury = "vivec's fury",
    shrinevivechumility = "vivec's humility", shrinevivecmystery = "vivec's mystery" }) do
    M.scripts[scriptId] = {
        kind = 'almsivi', services = { [0] = cures[0], [1] = cures[1], [2] = cures[2], [3] = { blessing } },
    }
end

function M.config(scriptId)
    return scriptId and M.scripts[string.lower(scriptId)]
end

function M.start(config, baseline, now)
    return { config = config, baseline = baseline, observed = {}, expires = now + 30 }
end

function M.observe(session, spell)
    if spell.caster or spell.item or spell.fromEquipment or not spell.activeSpellId then return end
    if session.baseline[spell.activeSpellId] then return end
    if not spell.effects or #spell.effects == 0 then return end
    session.observed[string.lower(spell.id)] = true
end

function M.step(session, questionState, button, now)
    if now > session.expires then return 'expired' end
    if questionState == 10 then session.sawMenu = true end
    if questionState == 20 then session.sawServices = true end
    if questionState == 0 and session.sawServices and session.completedAt == nil then
        session.completedAt = now
        session.button = button
    elseif questionState == 0 and session.sawMenu and not session.sawServices then
        return 'cancelled'
    end
    if session.completedAt then
        local spells = session.config.services[session.button]
        if not spells then return 'cancelled' end
        for _, id in ipairs(spells) do
            if session.observed[id] then return 'confirmed' end
        end
        if now - session.completedAt > 2 then return 'noEffect' end
    end
end

return M
