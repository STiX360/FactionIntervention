# Validation Report

Status: version 0.2.0 prepared for publication under the author's accepted standalone
OpenMW 0.51.0 scope. Modlist compatibility is not a release gate for this version.
Exact engine-level spell/teleport attribution remains a documented limitation.
Interactive tests were performed by the user, not by the agent; individual results
and corrections are recorded below.

## Evidence

Primary sources checked on 2026-10-08:

- Merlord's public description: https://www.nexusmods.com/morrowind/mods/46687
- OpenMW engine handlers: https://openmw.readthedocs.io/en/latest/reference/lua-scripting/engine_handlers.html
- OpenMW SpellCasting: https://openmw.readthedocs.io/en/latest/reference/lua-scripting/interface_spellcasting.html
- Engine handler order: https://github.com/OpenMW/openmw/blob/master/components/lua/scriptscontainer.hpp
- Local OpenMW API definitions and built-in playercontrols.lua, skillhandlers.lua,
  and spellcasting/interface_local.lua in MWSE-OpenMW-Bridge/sources/openmw.

The documented onFrame runs after input. Built-in playercontrols.lua creates a
one-frame controls.use pulse for spell casts. Engine handlers execute in direct
script order. A later player script can suppress that pulse with NoAttack before
mechanics starts the cast. This is a source-supported interception candidate.
The mock pre-cast test verifies pulse cancellation before a simulated consumer;
it does not prove actual engine mechanics order, load order, or every input path.
No onTeleported rollback or global teleport switch is used.

## Attribution Boundary

SkillProgression Spellcast_Success supplies skill/useType, not the actual spell
identity or teleport result. The prototype correlates an Intervention captured on
the input pulse with a Mysticism success, retaining it during the native spellcast
animation and bounding unanimated candidates to three seconds. Native teleport
restrictions are checked before debit. This still is not an engine spell-identity
or teleport-result hook: other scripts and late events can cause attribution errors.
The timeout is a prototype bound, not an engine guarantee. Those limitations mean
the correlated observations are not an unconditional guarantee for externally
modified casting behavior, even though the exercised standalone cases passed.

The latest SpellCasting interface offers apply-effects handlers and cast/source
information, but documentation alone does not establish that instant Intervention
effects traverse a cancellable handler before teleport. Its inflict method is a
stub in the inspected local script. Replacing the proxy with that hook requires
engine call-path verification and source-specific tests. No fallback silently
claims correctness. Engine tests alone will not remove a structural attribution
ambiguity; an appropriate source hook must be identified first.

## Tests and Scope

30 deterministic Python/engine-Lua-5.1 tests pass: both faction budgets, exhausted input
gate, failed cast/expiry, scroll/item exemption, Recall/power/weapons, promotion
and demotion/rejoin, rank capacity/configuration, save/load, disabled/copy state,
and malformed state sanitisation, fixture provisioning/save guard, and deferred
faction setup commands, three-day timers/catch-up/save migration, faction-specific
refills, shrine completion/cancellation, shared cures, old/repeated blessings,
wrong-source rejection, interaction save/load/expiry, and fixture home/time/affliction
helpers. All automated cases are API mocks; they do not replace the user engine
checks below. Arcane Misfires compatibility remains unverified.

Bridge and Arcane Misfires were inspected read-only for API and packaging
conventions. Their files and live game configuration were not edited. POTI's
Standard modlist was searched privately for Intervention duplication; no obvious
limiter entry was found. Name filtering is not proof of compatibility. The
modlist itself is not bundled or reproduced.

The original mod's reset/default semantics could not be verified from the public
description; its posts page was unavailable. Rank caps and the user-approved
shrine refill/three-day recovery rules are design choices, not a faithful port.

## Deliverable

Test ZIP includes independent Lua prototype, localization, mock tests, an isolated
manual launcher, installation instructions, and this report. It is labeled
0.2.0-prototype and is not presented as a functioning production release.

## Test Readiness Update

Household-Privileges-OpenMW was inspected read-only as the readiness reference.
Its separate test manifest, supplied scene fixtures, isolated direct-start profile,
concurrent-game guard, vanilla-data verification, and explicit acceptance table
informed this package's independently written harness. Household files were not edited.

The launcher targets installed OpenMW 0.51.0, starts in Seyda Neen, includes only
Morrowind.esm and the test manifest, and preserves test configuration under .runtime.
The fixture supplies four spells and four item types, initial nonmembership, high
casting stats, and test caps. Console helpers change membership/rank and magicka;
they never simulate the cast or alter production counters. Supply creation is
save-guarded to prevent duplication after reload. Fixture scripts are absent from
the production manifest.

verify_readiness.py confirms vanilla spell/faction records and both scroll and
cast-on-use clothing sources for each Intervention by parsing Morrowind.esm.
All six Lua scripts compile with the installed lua51.dll. PrepareOnly and launcher
syntax checks pass; the generated config was inspected. These are preparation
checks, not engine gameplay validation. See TESTING.md and reports/manual-results.md.

## Shrine and Recovery Update

The user confirmed capacity-only promotion, native paid/free shrine refills, and
one use per three in-game days with independent non-postponed timers. These rules
replace promotion renewal. Old spent counters/settings are retained on migration;
missing timer starts are initialized to current game time to avoid invented credit.

The OpenMW 0.51.0 source stores a caster reference only for actor casters:
https://github.com/OpenMW/openmw/blob/openmw-0.51.0/apps/openmw/mwmechanics/activespells.cpp
Therefore shrine effects have no caster object. The detector remembers activation,
observes the supported native script's questionstate 20 -> 0 completion and button,
and requires a new matching activeSpellId with effects and no actor/item source.
It samples while the session is active so it can retain short-lived observations.
No refill occurs solely from a menu transition, gold loss, proximity, gaze, or
pre-existing blessing. No vanilla script/record is replaced by the production mod.

Supported native layouts are Imperial, Temple, Veloth, Vivec Fury/Humility/Mystery.
Quest/pilgrimage scripts and modified scripts with different layouts are unsupported.
This remains correlation rather than preserved caster identity; another mod injecting
the same source-less spell during a completed matching service is a residual risk.
Instant cures or restoration effects may disappear before the Lua snapshot; in
that case the detector logs noEffect and does not refill. User-run tests explicitly
exercise those cases. There is no silent script-completion-only fallback.

The fixture creates two labelled activators retaining native shrine scripts, gives
500 gold, and supplies home/time-advance/affliction helpers. Test helpers never refill
the production allowance. Time helpers change real game time, which the production
recovery logic then observes. No game was launched by the agent.

On 2026-10-09 the user reported promotion, free shrine refills, and timed recovery
working in the test session. Shared disease/blight cure visibility remains unverified.
The subsequent save/load test failed: openmw.log recorded test_fixtures.lua onSave
"Value is not serializable." The saved home contained a Cell object; failure lost
the setup guard and reload repeated initialization, removing both memberships.
Home now stores only cell-name and numeric coordinates, reconstructing Vector3 on
teleport. Loading missing fixture data also suppresses initialization. Two added
regressions check plain saved values, preserved membership/home, and missing-data
safety. The corrected engine save/load test still needs a user rerun; the old test
save cannot establish timer persistence because nonmembership reset its progress.
The user subsequently confirmed the corrected save/load rerun and the shared
disease/blight cure walkthrough working.

## Disabled Teleport Debit Fix

The user's next screenshot showed a Divine cast with native teleportation disabled:
position remained in Seyda Neen, but used changed 0 -> 1 and a timer started.
The success handler now checks types.Player.isTeleportingEnabled(self) before any
debit, clearing the pending candidate when false. It never changes that flag or
suppresses the engine's own blocked-cast behavior. Two regression tests cover both
factions, no new timer, unchanged existing timer, restrictions changing during a
cast, candidate clearing, and normal debit after re-enabling. All 25 tests pass;
the corrected in-game blocked-teleport check is awaiting a user rerun. This narrow
guard does not establish actual cast identity or eliminate spell-switch attribution.

The user confirmed the disabled-teleport fix, insufficient-magicka refusal, failed
casting rolls, and scroll/item exemptions working. Spell switching still failed:
the original Intervention teleported, but selection had changed and neither budget
was debited. The completion-time selected-spell comparison has now been removed.
While openmw.animation.isPlaying(self, 'spellcast') is true, input handling retains
the original candidate and ignores replacement attempts, including Mark -> Divine.
Candidates observed casting are cleared when that animation ends without success;
success clears them immediately. Settings disablement, native teleport restrictions,
save/load clearing, and unanimated expiry remain guarded. Five new regressions cover
both switch directions, repeated button use, switching to Mark/items, Mark -> Divine,
cancelled casts, duplicate successes, and long/stale animation timing. All 30 tests
pass; the updated switching behavior still requires an in-game rerun.

The user subsequently confirmed all four switching cases working after the fix.
The additional cast-button-during-animation exercise was skipped, not passed.
Final checks reran all 30 automated cases and readiness validation successfully.
The production manifest contains only player.lua and shrines.lua, excluding the
fixture/player test helpers. The test ZIP was rebuilt and its integrity verified.
No additional change was made to production behavior during this final check.

Earlier readiness verdict: tested beta for the exercised vanilla OpenMW 0.51.0
scenarios, not an unconditional production release. The input/animation/skill correlation
still cannot identify every externally injected or delayed cast event. Production
manifest installation, actual modlist compatibility, custom mixed-effect spells,
and the skipped repeat-input case are not established by this isolated suite.
Arcane Misfires or other casting hooks require separate compatibility validation.

Source checked for this fix:
https://github.com/OpenMW/openmw/blob/openmw-0.51.0/apps/openmw/mwmechanics/character.cpp
(original spell captured at casting start, not GUI selection changes), and
https://github.com/OpenMW/openmw/blob/openmw-0.51.0/files/lua_api/openmw/animation.lua
(isPlaying availability). Installed 0.51.0 playercontrols.lua supplies the one-frame
input pulse. The fix remains a correlated input/animation/skill observation, not a
new guaranteed spell-specific successful-teleport API.

## Accepted Publication Scope

The author explicitly accepted standalone operation as sufficient for publication,
with other-mod compatibility addressed from reports. Version 0.2.0 is prepared on
that basis, without implying the attribution mechanism or compatibility was changed.
README.md now documents casting/animation/skill/input overhauls, other Intervention
limiters, replacement shrine scripts, faction changes, and mixed-effect spells.
Animation risks distinguish behavior/event changes from visual-only replacements;
no specific animation mod is declared a confirmed conflict without evidence.

The production archive uses an explicit eight-file allowlist: manifest, four runtime
Lua modules, localization, README, and release notes. The isolated launcher, test
manifest/helpers, saves, game assets, dependencies, and developer reports are excluded.
The development archive remains available with tools/package.py --test. No upload
or modification of the author's live game configuration was performed.

## Optional Item Limits in 0.3.0

Added a saved exemptItems checkbox defaulting to true. Setting it false extends the
existing pre-cast faction/capacity gate to selected CastOnce and CastOnUse Intervention
enchantments. Saves missing the new setting migrate to the original exempt behavior.
Switching modes does not modify spent counters or recovery timestamps. Recall-bearing,
constant-effect, cast-on-strike, and non-Intervention enchantments are excluded.

OpenMW 0.51.0 reports successful CastOnUse items through Enchant_UseMagicItem only
after sufficient charge has been checked; its CastOnce branch removes one item and
does not issue a skill-success notification:
https://github.com/OpenMW/openmw/blob/openmw-0.51.0/apps/openmw/mwmechanics/spellcasting.cpp
The optional item mode therefore matches a captured item candidate to that Enchant
notification, or observes a captured scroll record's inventory count decreasing.
Completion clears the candidate, checks the enabled/exemption/teleport flags, and
then uses the same debit and timer logic as spells. Scroll consumption is checked
before finished-animation cleanup; expired unanimated requests cannot claim later
inventory changes. Source selection during an animation cannot replace the candidate.

This remains correlated accounting: other mods changing inventory during the pending
scroll window can affect attribution. God-mode scroll casting consumes no item and
is unsupported by consumption tracking. No resource rollback is attempted when a
native teleport restriction causes an otherwise successful item cast to have no effect.

Eight additional automated tests cover shared budgets, both factions, source-specific
success signals, consumed-scroll detection without a skill event, empty/failure and
restriction cases, source switches, passive/Recall exemptions, candidate cancellation,
expiry, settings persistence and old-save defaults. All 38 runtime tests pass. The
non-default item-limiting mode has not been tested in-game; its walkthrough and result
rows explicitly remain pending. The 0.2.0 production archive is preserved unchanged;
0.3.0 gets separate production and development archives.
