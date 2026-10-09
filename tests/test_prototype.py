"""Execute mock tests with engine Lua 5.1; mock timing is not engine proof."""
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
from lua_runtime import LuaRuntime


class PrototypeTests(unittest.TestCase):
    def tearDown(self):
        self.lua.close()

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().root = ROOT.as_posix()
        self.lua.execute("""
            package.path = root .. '/?.lua;' .. package.path
            values = {}
            section = {get=function(_, k) return values[k] end,
                       set=function(_, k, v) values[k]=v end}
            clock = 0
            gameTime = 0
            stance = 'spell'
            enchanted = nil
            teleportingEnabled = true
            casting = false
            inventoryCounts = {}
            enchantments = {}
            itemType = {record=function(item) return item.record end}
            ranks = {['imperial cult']=1, temple=1}
            messages = {}
            actor = {controls={use=0}, ATTACK_TYPE={NoAttack=0, Any=1}}
            core = {getSimulationTime=function() return clock end,
                    getGameTime=function() return gameTime end,
                    magic={SPELL_TYPE={Spell='spell'}, EFFECT_TYPE={Recall='recall'},
                        ENCHANTMENT_TYPE={CastOnce=0,CastOnUse=2,CastOnStrike=1,ConstantEffect=3},
                        enchantments={records=enchantments}}}
            interfaces = {
                Settings={registerPage=function() end, registerGroup=function(g)
                    for _, s in ipairs(g.settings) do values[s.key]=s.default end
                end},
                SkillProgression={SKILL_USE_TYPES={Spellcast_Success=0,Enchant_UseMagicItem=1},
                    addSkillUsedHandler=function(f) success=f end}
            }
            package.preload['openmw.core']=function() return core end
            package.preload['openmw.animation']=function() return {
                hasAnimation=function() return true end,
                isPlaying=function(_,group) assert(group=='spellcast'); return casting end} end
            package.preload['openmw.self']=function() return actor end
            package.preload['openmw.storage']=function()
                return {playerSection=function() return section end} end
            package.preload['openmw.ui']=function()
                return {showMessage=function(m) messages[#messages+1]=m end} end
            package.preload['openmw.interfaces']=function() return interfaces end
            package.preload['openmw.types']=function() return {
                Player={isTeleportingEnabled=function() return teleportingEnabled end},
                NPC={getFactionRank=function(_, id) return ranks[id] end},
                Actor={STANCE={Spell='spell'}, getStance=function() return stance end,
                    inventory=function() return {countOf=function(_,id) return inventoryCounts[id] or 0 end} end,
                    getSelectedEnchantedItem=function() return enchanted end,
                    getSelectedSpell=function() return spell end}}
            end
            policy = require('scripts.faction_intervention.policy')
            mod = require('scripts.faction_intervention.player')
            function selectSpell(kind)
                spell={id=kind, type='spell', effects={{id=policy.effects[kind]}}}
            end
            function attempt(kind)
                selectSpell(kind); actor.controls.use=1; mod.engineHandlers.onFrame()
            end
            function selectItem(kind,source)
                local id=source .. '-' .. kind
                enchantments[id]={type=source=='scroll' and 0 or 2,effects={{id=policy.effects[kind]}}}
                inventoryCounts[id]=inventoryCounts[id] or 10
                enchanted={type=itemType,record={id=id,enchant=id}}
                return id
            end
            function attemptItem(kind,source)
                local id=selectItem(kind,source)
                actor.controls.use=1; mod.engineHandlers.onFrame()
                return id
            end
        """)

    def check(self, code):
        self.lua.execute(code)

    def test_both_factions_and_exhaustion(self):
        self.check("""
            for _, kind in ipairs({'divine','almsivi'}) do
                attempt(kind); assert(actor.controls.use==1)
                success('mysticism', {useType=0})
                assert(mod.interface.getState().used[kind]==1)
                attempt(kind); assert(actor.controls.use==0)
                assert(messages[#messages]:find('Intervention refused'))
            end
        """)

    def test_pre_cast_control_gate(self):
        self.check("""
            ranks['imperial cult']=0
            attempt('divine')
            local castStarted = actor.controls.use ~= actor.ATTACK_TYPE.NoAttack
            assert(not castStarted)
            assert(mod.interface.getState().used.divine==0)
        """)

    def test_switching_interventions_charges_original_spell_once(self):
        self.check("""
            for _,kind in ipairs({'divine','almsivi'}) do
                local other=kind=='divine' and 'almsivi' or 'divine'
                attempt(kind)
                casting=true
                selectSpell(other)
                actor.controls.use=1; mod.engineHandlers.onFrame()
                local before=mod.interface.getState()
                success('mysticism', {useType=0})
                success('mysticism', {useType=0})
                local after=mod.interface.getState()
                assert(after.used[kind]==before.used[kind]+1)
                assert(after.used[other]==before.used[other])
                casting=false; actor.controls.use=0; mod.engineHandlers.onFrame()
            end
        """)

    def test_switching_to_mark_or_item_retains_original_intervention(self):
        self.check("""
            values.divineRank1=3
            for _,source in ipairs({'mark','item'}) do
                attempt('divine'); casting=true
                if source=='mark' then spell={id='mark',type='spell',effects={{id='mark'}}}
                else enchanted={id='scroll'} end
                actor.controls.use=1; mod.engineHandlers.onFrame()
                success('mysticism', {useType=0})
                casting=false; enchanted=nil; actor.controls.use=0; mod.engineHandlers.onFrame()
            end
            assert(mod.interface.getState().used.divine==2)
            assert(mod.interface.getState().used.almsivi==0)
        """)

    def test_mark_cast_cannot_acquire_intervention_candidate_mid_animation(self):
        self.check("""
            spell={id='mark',type='spell',effects={{id='mark'}}}
            actor.controls.use=1; mod.engineHandlers.onFrame()
            casting=true; selectSpell('divine')
            actor.controls.use=1; mod.engineHandlers.onFrame()
            success('mysticism', {useType=0})
            assert(mod.interface.getState().used.divine==0)
            assert(mod.interface.getState().recovery.divine==nil)
        """)

    def test_cancelled_cast_does_not_charge_a_later_mark(self):
        self.check("""
            attempt('divine'); casting=true; actor.controls.use=0
            mod.engineHandlers.onFrame()
            casting=false; mod.engineHandlers.onFrame()
            spell={id='mark',type='spell',effects={{id='mark'}}}
            success('mysticism', {useType=0})
            assert(mod.interface.getState().used.divine==0)
        """)

    def test_long_animation_keeps_candidate_but_stale_success_expires(self):
        self.check("""
            attempt('divine'); casting=true
            clock=4; actor.controls.use=0; mod.engineHandlers.onFrame()
            selectSpell('almsivi'); success('mysticism', {useType=0})
            assert(mod.interface.getState().used.divine==1)
            casting=false; attempt('almsivi')
            clock=8; success('mysticism', {useType=0})
            assert(mod.interface.getState().used.almsivi==0)
        """)

    def test_disabled_teleport_casts_never_spend_or_start_timers(self):
        self.check("""
            teleportingEnabled=false
            for _,kind in ipairs({'divine','almsivi'}) do
                attempt(kind); assert(actor.controls.use==1)
                success('mysticism', {useType=0})
                local state=mod.interface.getState()
                assert(state.used[kind]==0 and state.recovery[kind]==nil)
            end
            teleportingEnabled=true
            success('mysticism', {useType=0})
            assert(mod.interface.getState().used.almsivi==0)
            for _,kind in ipairs({'divine','almsivi'}) do
                attempt(kind); success('mysticism', {useType=0})
                assert(mod.interface.getState().used[kind]==1)
                assert(mod.interface.getState().recovery[kind]==0)
            end
        """)

    def test_disabled_teleport_checks_completion_and_preserves_existing_timer(self):
        self.check("""
            values.divineRank1=3
            attempt('divine'); success('mysticism', {useType=0})
            gameTime=86400
            attempt('divine')
            teleportingEnabled=false
            success('mysticism', {useType=0})
            local state=mod.interface.getState()
            assert(state.used.divine==1 and state.recovery.divine==0)
            assert(mod.interface.getRemaining('divine')==2)
        """)

    def test_failed_cast_and_expired_candidate(self):
        self.check("""
            attempt('divine')
            success('mysticism', {useType=1})
            assert(mod.interface.getState().used.divine==0)
            clock=4; actor.controls.use=0; mod.engineHandlers.onFrame()
            success('mysticism', {useType=0})
            assert(mod.interface.getState().used.divine==0)
        """)

    def test_scroll_and_enchanted_item_exemptions(self):
        self.check("""
            ranks['imperial cult']=0
            for _, source in ipairs({'scroll', 'ring'}) do
                enchanted={id=source}; attempt('divine')
                assert(actor.controls.use==1)
                success('mysticism', {useType=0})
                assert(mod.interface.getState().used.divine==0)
            end
        """)

    def test_limited_items_require_membership_and_share_spell_budget(self):
        self.check("""
            values.exemptItems=false
            for _,kind in ipairs({'divine','almsivi'}) do
                local faction=policy.factions[kind].id
                ranks[faction]=0
                for _,source in ipairs({'scroll','item'}) do
                    attemptItem(kind,source); assert(actor.controls.use==0)
                end
                ranks[faction]=1; enchanted=nil
                attempt(kind); success('mysticism', {useType=0})
                for _,source in ipairs({'scroll','item'}) do
                    attemptItem(kind,source); assert(actor.controls.use==0)
                end
                assert(mod.interface.getState().used[kind]==1)
            end
        """)

    def test_limited_cast_on_use_items_charge_correct_faction_once(self):
        self.check("""
            values.exemptItems=false
            for _,kind in ipairs({'divine','almsivi'}) do
                attemptItem(kind,'item'); assert(actor.controls.use==1)
                success('mysticism', {useType=0})
                success('enchant', {useType=0})
                assert(mod.interface.getState().used[kind]==0)
                success('enchant', {useType=1})
                success('enchant', {useType=1})
                assert(mod.interface.getState().used[kind]==1)
                assert(mod.interface.getState().recovery[kind]==0)
                enchanted=nil; attempt(kind)
                assert(actor.controls.use==0)
            end
        """)

    def test_limited_scrolls_charge_on_consumption_without_skill_event(self):
        self.check("""
            values.exemptItems=false
            for _,kind in ipairs({'divine','almsivi'}) do
                local id=attemptItem(kind,'scroll')
                actor.controls.use=0
                success('mysticism',{useType=0}); success('enchant',{useType=1})
                mod.engineHandlers.onFrame()
                assert(mod.interface.getState().used[kind]==0)
                inventoryCounts[id]=inventoryCounts[id]-1
                enchanted=nil; spell=nil
                mod.engineHandlers.onFrame(); mod.engineHandlers.onFrame()
                assert(mod.interface.getState().used[kind]==1)
                assert(mod.interface.getState().recovery[kind]==0)
            end
        """)

    def test_failed_empty_or_teleport_disabled_item_casts_do_not_debit(self):
        self.check("""
            values.exemptItems=false
            attemptItem('divine','item')
            actor.controls.use=0; casting=true; mod.engineHandlers.onFrame()
            casting=false; mod.engineHandlers.onFrame()
            success('enchant',{useType=1})
            assert(mod.interface.getState().used.divine==0)
            teleportingEnabled=false
            attemptItem('divine','item'); success('enchant',{useType=1})
            local id=attemptItem('almsivi','scroll')
            inventoryCounts[id]=inventoryCounts[id]-1
            actor.controls.use=0; mod.engineHandlers.onFrame()
            local state=mod.interface.getState()
            assert(state.used.divine==0 and state.used.almsivi==0)
            assert(state.recovery.divine==nil and state.recovery.almsivi==nil)
        """)

    def test_item_toggle_and_old_save_migration_preserve_counters(self):
        self.check("""
            assert(values.exemptItems==true)
            attempt('divine'); success('mysticism',{useType=0})
            values.exemptItems=false
            local data=mod.engineHandlers.onSave()
            assert(data.settings.exemptItems==false)
            values.exemptItems=true; mod.engineHandlers.onLoad(data)
            actor.controls.use=0; mod.engineHandlers.onFrame()
            assert(values.exemptItems==false and mod.interface.getState().used.divine==1)
            data.settings.exemptItems=nil
            mod.engineHandlers.onLoad(data); mod.engineHandlers.onFrame()
            assert(values.exemptItems==true and mod.interface.getState().used.divine==1)
            attemptItem('divine','item'); assert(actor.controls.use==1)
            success('enchant',{useType=1})
            assert(mod.interface.getState().used.divine==1)
        """)

    def test_item_switching_preserves_original_faction_and_source(self):
        self.check("""
            values.exemptItems=false
            attemptItem('divine','item'); casting=true
            selectItem('almsivi','item'); actor.controls.use=1; mod.engineHandlers.onFrame()
            success('enchant',{useType=1})
            assert(mod.interface.getState().used.divine==1)
            assert(mod.interface.getState().used.almsivi==0)
            casting=false; actor.controls.use=0; mod.engineHandlers.onFrame()
            local id=attemptItem('almsivi','scroll'); casting=true
            enchanted=nil; selectSpell('divine')
            actor.controls.use=1; mod.engineHandlers.onFrame()
            inventoryCounts[id]=inventoryCounts[id]-1
            casting=false; actor.controls.use=0; mod.engineHandlers.onFrame()
            assert(mod.interface.getState().used.divine==1)
            assert(mod.interface.getState().used.almsivi==1)
        """)

    def test_nonintervention_recall_and_passive_enchantments_remain_unrestricted(self):
        self.check("""
            values.exemptItems=false; ranks['imperial cult']=0
            local id=selectItem('divine','item')
            for _,effects in ipairs({{{id='restorehealth'}},{{id='divineintervention'},{id='recall'}}}) do
                enchantments[id].effects=effects
                actor.controls.use=1; mod.engineHandlers.onFrame()
                assert(actor.controls.use==1)
                success('enchant',{useType=1})
                assert(mod.interface.getState().used.divine==0)
            end
            enchantments[id].effects={{id='divineintervention'}}
            for _,enchantType in ipairs({1,3}) do
                enchantments[id].type=enchantType
                actor.controls.use=1; mod.engineHandlers.onFrame()
                assert(actor.controls.use==1)
            end
        """)

    def test_scroll_timeout_cancellation_and_mid_cast_exemption(self):
        self.check("""
            values.exemptItems=false
            local id=attemptItem('divine','scroll')
            actor.controls.use=0; clock=4
            inventoryCounts[id]=inventoryCounts[id]-1
            mod.engineHandlers.onFrame()
            assert(mod.interface.getState().used.divine==0)
            id=attemptItem('divine','scroll')
            casting=true; mod.engineHandlers.onFrame()
            casting=false; actor.controls.use=0; mod.engineHandlers.onFrame()
            inventoryCounts[id]=inventoryCounts[id]-1; mod.engineHandlers.onFrame()
            assert(mod.interface.getState().used.divine==0)
            id=attemptItem('divine','scroll')
            values.exemptItems=true; inventoryCounts[id]=inventoryCounts[id]-1
            actor.controls.use=0; mod.engineHandlers.onFrame()
            assert(mod.interface.getState().used.divine==0)
        """)

    def test_recall_power_and_weapons_untouched(self):
        self.check("""
            ranks['imperial cult']=0
            for _, kind in ipairs({'recall','power','weapon'}) do
                selectSpell('divine')
                if kind=='recall' then spell.effects={{id='recall'}} end
                if kind=='power' then spell.type='power' end
                stance=kind=='weapon' and 'weapon' or 'spell'
                actor.controls.use=1; mod.engineHandlers.onFrame()
                assert(actor.controls.use==1)
            end
        """)

    def test_promotion_demotion_and_rejoining(self):
        self.check("""
            attempt('divine'); success('mysticism', {useType=0})
            ranks['imperial cult']=3; attempt('divine')
            assert(mod.interface.getState().used.divine==1)
            success('mysticism', {useType=0})
            ranks['imperial cult']=0; attempt('divine')
            ranks['imperial cult']=3; attempt('divine')
            assert(mod.interface.getState().used.divine==2)
        """)

    def test_configurable_capacity_without_promotion_refill(self):
        self.check("""
            attempt('almsivi'); success('mysticism', {useType=0})
            ranks.temple=2; values.almsiviRank2=4; attempt('almsivi')
            assert(mod.interface.getState().used.almsivi==1)
            assert(mod.interface.getRemaining('almsivi')==3)
        """)

    def test_save_load_settings_and_independent_budgets(self):
        self.check("""
            values.divineRank1=7
            attempt('divine'); success('mysticism', {useType=0})
            local data=mod.engineHandlers.onSave()
            values.divineRank1=0
            mod.engineHandlers.onLoad(data)
            actor.controls.use=0; mod.engineHandlers.onFrame()
            assert(values.divineRank1==7)
            assert(mod.interface.getRemaining('divine')==6)
            assert(mod.interface.getState().used.almsivi==0)
        """)

    def test_disabled_and_state_copy(self):
        self.check("""
            values.enabled=false; ranks.temple=0; attempt('almsivi')
            assert(actor.controls.use==1)
            local copy=mod.interface.getState(); copy.used.divine=99
            assert(mod.interface.getState().used.divine==0)
        """)

    def test_state_sanitising(self):
        self.check("""
            local state=policy.normaliseState({used={divine=-1,almsivi=0/0},
                bestRank={divine=100}})
            assert(state.used.divine==0 and state.used.almsivi==0)
            assert(state.bestRank.divine==10)
        """)

    def test_timer_survives_further_casts_and_restores_one_per_interval(self):
        self.check("""
            values.divineRank1=4
            attempt('divine'); success('mysticism', {useType=0})
            gameTime=86400
            attempt('divine'); success('mysticism', {useType=0})
            assert(mod.interface.getState().recovery.divine==0)
            actor.controls.use=0
            gameTime=259199; mod.engineHandlers.onFrame()
            assert(mod.interface.getState().used.divine==2)
            gameTime=259200; mod.engineHandlers.onFrame()
            assert(mod.interface.getState().used.divine==1)
            assert(mod.interface.getState().recovery.divine==259200)
            gameTime=518400; mod.engineHandlers.onFrame()
            assert(mod.interface.getState().used.divine==0)
            assert(mod.interface.getState().recovery.divine==nil)
            gameTime=9999999; mod.engineHandlers.onFrame()
            attempt('divine'); success('mysticism', {useType=0})
            assert(mod.interface.getState().recovery.divine==gameTime)
        """)

    def test_recovery_catchup_save_load_and_old_save_migration(self):
        self.check("""
            values.divineRank1=4
            for i=1,3 do attempt('divine'); success('mysticism', {useType=0}) end
            gameTime=100000
            local data=mod.engineHandlers.onSave()
            mod.engineHandlers.onLoad(data)
            actor.controls.use=0
            gameTime=600000; mod.engineHandlers.onFrame()
            assert(mod.interface.getState().used.divine==1)
            assert(mod.interface.getState().recovery.divine==518400)
            mod.engineHandlers.onLoad({version=1,used={divine=1}})
            mod.engineHandlers.onFrame()
            assert(mod.interface.getState().used.divine==1)
            assert(mod.interface.getState().recovery.divine==600000)
        """)

    def test_shrine_refills_only_matching_faction_and_stops_timer(self):
        self.check("""
            attempt('divine'); success('mysticism', {useType=0})
            attempt('almsivi'); success('mysticism', {useType=0})
            mod.eventHandlers.FactionInterventionShrineCompleted({kind='divine'})
            local state=mod.interface.getState()
            assert(state.used.divine==0 and state.recovery.divine==nil)
            assert(state.used.almsivi==1 and state.recovery.almsivi==0)
            ranks.temple=0
            mod.eventHandlers.FactionInterventionShrineCompleted({kind='almsivi'})
            assert(mod.interface.getState().used.almsivi==1)
        """)


class ShrineTests(unittest.TestCase):
    def tearDown(self):
        self.lua.close()

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().root = ROOT.as_posix()
        self.lua.execute("""
            package.path=root .. '/?.lua;' .. package.path
            clock=0; active={}; sent={}; vars={questionstate=0,button=-1}
            cell={}
            types={Player={},Activator={},Actor={}}
            actor={id='player',type=types.Player,cell=cell,isValid=function() return true end,
                sendEvent=function(_,name,data) sent[#sent+1]={name=name,data=data} end}
            altar={id='altar',recordId='imperial',type=types.Activator,cell=cell,
                isValid=function() return true end,mwscript='shrineImperial'}
            temple={id='temple',recordId='tribunal',type=types.Activator,cell=cell,
                isValid=function() return true end,mwscript='shrineTemple'}
            types.Activator.record=function(obj) return obj end
            types.Actor.activeSpells=function() return active end
            package.preload['openmw.types']=function() return types end
            package.preload['openmw.core']=function() return {getSimulationTime=function() return clock end} end
            package.preload['openmw.world']=function() return {mwscript={getLocalScript=function()
                return {variables=vars} end}} end
            package.preload['openmw.interfaces']=function() return {Activation={addHandlerForType=function(_,f)
                activate=f end}} end
            shrines=require('scripts.faction_intervention.shrines')
            function step(state,button)
                vars.questionstate=state; vars.button=button or -1; shrines.engineHandlers.onUpdate()
            end
            function effect(id,instance,caster)
                active[#active+1]={id=id,activeSpellId=instance or 'new',caster=caster,effects={{id='effect'}}}
            end
        """)

    def test_paid_and_free_services_correlate_shared_cures(self):
        self.lua.execute("""
            for _,object in ipairs({altar,temple}) do
                active={}; assert(activate(object,actor)==nil)
                step(10); step(20)
                effect('cure poison touch','new-' .. object.id)
                step(0,2)
                assert(sent[#sent].data.kind==(object==altar and 'divine' or 'almsivi'))
            end
            assert(#sent==2 and shrines.interface.getDiagnostics().confirmed==2)
        """)

    def test_cancel_and_no_affliction_never_refill(self):
        self.lua.execute("""
            activate(altar,actor); step(10); step(0,1)
            assert(#sent==0 and shrines.interface.getDiagnostics().cancelled==1)
            activate(temple,actor); step(10); step(20); step(0,0)
            clock=3; step(0,0)
            assert(#sent==0 and shrines.interface.getDiagnostics().noEffect==1)
        """)

    def test_old_blessing_rejected_and_repeat_new_blessing_accepted(self):
        self.lua.execute("""
            effect("lady's grace shrine",'old')
            activate(temple,actor); step(10); step(20); step(0,3)
            assert(#sent==0)
            effect("lady's grace shrine",'new')
            step(0,3); assert(#sent==1)
            step(0,3); assert(#sent==1)
            activate(temple,actor); step(10); step(20)
            effect("lady's grace shrine",'repeat')
            step(0,3); assert(#sent==2)
        """)

    def test_wrong_service_and_actor_casts_rejected(self):
        self.lua.execute("""
            activate(temple,actor); step(10); step(20)
            effect('soul of sotha sil','unrelated')
            effect("lady's grace shrine",'selfcast',actor)
            step(0,3); clock=3; step(0,3)
            assert(#sent==0)
        """)

    def test_switch_shrine_save_load_and_expiry(self):
        self.lua.execute("""
            activate(altar,actor); step(10)
            activate(temple,actor); step(10); step(20)
            effect('restore attributes')
            step(0,3); clock=3; step(0,3); assert(#sent==0)
            activate(temple,actor); step(10); step(20)
            shrines.engineHandlers.onSave()
            effect("lady's grace shrine",'after-save'); step(0,3); assert(#sent==0)
            activate(temple,actor); step(20)
            shrines.engineHandlers.onLoad(); step(0,3); assert(#sent==0)
            activate(altar,actor); clock=40; step(0,3)
            assert(shrines.interface.getDiagnostics().expired==1)
        """)


class FixtureTests(unittest.TestCase):
    def tearDown(self):
        self.lua.close()

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().root = ROOT.as_posix()
        self.lua.execute("""
            package.path=root .. '/?.lua;' .. package.path
            spells={}; items={}; events={}; values={}; shrines={}; advanced=0; returnedHome=false
            ranks={['imperial cult']=0, temple=0}
            joins={}
            function stat() return {base=100,current=100} end
            magicka=stat(); fatigue=stat(); mysticism=stat(); willpower=stat(); luck=stat()
            vectorMT={__add=function(a,b) return a end,__tostring=function() return 'position' end}
            player={type='player',cell={name='Seyda Neen'}, position=setmetatable({x=1,y=2,z=3},vectorMT),
                teleport=function(_,cell,position)
                    assert(cell=='Seyda Neen' and position.x==1 and position.y==2 and position.z==3)
                    returnedHome=true end,
                sendEvent=function(_, name, data) events[#events+1]={name,data} end}
            player.object=player
            package.preload['openmw.util']=function() return {vector3=function(x,y,z)
                return {x=x,y=y,z=z} end} end
            local ench={ds={type=0,effects={{id='divineintervention'}}},
                as={type=0,effects={{id='almsiviintervention'}}},
                di={type=2,effects={{id='divineintervention'}}},
                ai={type=2,effects={{id='almsiviintervention'}}}}
            package.preload['openmw.core']=function() return {getGameTime=function() return 0 end,
                sendGlobalEvent=function(_,data) fixtures.eventHandlers.FactionInterventionTestAction(data) end, magic={
                SPELL_TYPE={Disease='disease',Blight='blight'},
                ENCHANTMENT_TYPE={CastOnce=0,CastOnUse=2}, enchantments={records=ench},
                spells={records={['divine intervention']={},['almsivi intervention']={},
                    mark={},recall={}, {id='test-disease',name='Test Disease',type='disease'},
                    {id='test-blight',name='Test Blight',type='blight'}}}}} end
            package.preload['openmw.world']=function() return {
                advanceTime=function(hours) advanced=advanced+hours end,
                createRecord=function(draft) return {id=draft.name,mwscript=draft.template.mwscript} end,
                createObject=function(id,count)
                return {moveInto=function(_,target)
                    assert(target==player); items[#items+1]={id=id,count=count}
                end,teleport=function() shrines[#shrines+1]=id end}
            end} end
            package.preload['openmw.types']=function() return {
                Player='player',
                Activator={record=function(id) return {id=id,mwscript='shrineScript'} end,
                    createRecordDraft=function(draft) return draft end},
                Book={records={{id='divine-scroll',enchant='ds'},{id='almsivi-scroll',enchant='as'}}},
                Clothing={records={{id='divine-ring',enchant='di'},{id='almsivi-ring',enchant='ai'}}},
                Actor={spells=function() return {add=function(_,id) spells[#spells+1]=id end} end,
                    stats={dynamic={magicka=function() return magicka end,
                        fatigue=function() return fatigue end}}},
                NPC={leaveFaction=function(_,id) ranks[id]=0 end,
                    joinFaction=function(_,id) joins[id]=true end,
                    getFactionRank=function(_,id) return ranks[id] end,
                    setFactionRank=function(_,id,rank)
                        assert(ranks[id]>0, 'rank set before queued join'); ranks[id]=rank end,
                    stats={skills={mysticism=function() return mysticism end},
                        attributes={willpower=function() return willpower end,luck=function() return luck end}}}}
            end
            package.preload['openmw.self']=function() return player end
            package.preload['openmw.storage']=function() return {playerSection=function()
                return {set=function(_,k,v) values[k]=v end} end} end
            package.preload['openmw.ui']=function() return {showMessage=function() end} end
            package.preload['openmw.interfaces']=function() return {FactionIntervention={
                getState=function() return {used={divine=1,almsivi=0},recovery={}} end,
                getRemaining=function() return 0 end}} end
            fixtures=require('scripts.faction_intervention.test_fixtures')
            testPlayer=require('scripts.faction_intervention.test_player')
        """)

    def test_supplies_once_and_saved_guard(self):
        self.lua.execute("""
            fixtures.engineHandlers.onPlayerAdded(player)
            assert(#spells==4 and #items==5 and #events==1 and #shrines==2)
            assert(items[1].count==10 and items[2].count==1)
            assert(items[3].count==10 and items[4].count==1)
            assert(fixtures.engineHandlers.onSave().done==true)
            fixtures.engineHandlers.onLoad(fixtures.engineHandlers.onSave())
            fixtures.engineHandlers.onPlayerAdded(player)
            assert(#items==5 and #spells==4 and #shrines==2)
            testPlayer.eventHandlers.FactionInterventionFixtureReady()
            assert(values.divineRank1==1 and values.almsiviRank3==2)
            assert(magicka.current==500 and mysticism.base==100)
        """)

    def test_deferred_join_and_setup_commands(self):
        self.lua.execute("""
            testPlayer.interface.run('promote')
            testPlayer.engineHandlers.onFrame()
            assert(ranks.temple==0)
            for id in pairs(joins) do ranks[id]=1 end
            testPlayer.engineHandlers.onFrame()
            assert(ranks.temple==3 and ranks['imperial cult']==3)
            testPlayer.interface.run('fail'); assert(magicka.current==0)
            testPlayer.interface.run('ready'); assert(magicka.current==500)
            testPlayer.interface.run('nonmember'); assert(ranks.temple==0)
            assert(testPlayer.interface.status():find('used=1'))
        """)

    def test_home_save_contains_only_plain_values_and_preserves_membership(self):
        self.lua.execute("""
            fixtures.engineHandlers.onPlayerAdded(player)
            ranks.temple=3; ranks['imperial cult']=3
            local saved=fixtures.engineHandlers.onSave()
            local function serializable(value)
                if type(value)=='table' then
                    assert(getmetatable(value)==nil, 'engine object in saved fixture data')
                    for key,item in pairs(value) do serializable(key); serializable(item) end
                else
                    assert(type(value)=='number' or type(value)=='string' or type(value)=='boolean')
                end
            end
            serializable(saved)
            assert(saved.home.cell=='Seyda Neen' and saved.home.x==1 and saved.home.z==3)
            fixtures.engineHandlers.onLoad(saved)
            fixtures.engineHandlers.onPlayerAdded(player)
            assert(ranks.temple==3 and ranks['imperial cult']==3)
            assert(#items==5 and #shrines==2)
            testPlayer.interface.run('home'); assert(returnedHome)
        """)

    def test_missing_fixture_save_never_repeats_membership_reset(self):
        self.lua.execute("""
            ranks.temple=3; ranks['imperial cult']=3
            fixtures.engineHandlers.onLoad(nil)
            fixtures.engineHandlers.onPlayerAdded(player)
            assert(ranks.temple==3 and ranks['imperial cult']==3)
            assert(#items==0 and #shrines==0)
            assert(fixtures.engineHandlers.onSave().done==true)
        """)

    def test_home_time_and_affliction_helpers(self):
        self.lua.execute("""
            fixtures.engineHandlers.onPlayerAdded(player)
            testPlayer.interface.run('home'); assert(returnedHome)
            testPlayer.interface.run('day'); assert(advanced==24)
            testPlayer.interface.run('three-days'); assert(advanced==96)
            testPlayer.interface.run('disease'); assert(spells[#spells]=='test-disease')
            testPlayer.interface.run('blight'); assert(spells[#spells]=='test-blight')
        """)


if __name__ == '__main__':
    unittest.main(verbosity=2)
