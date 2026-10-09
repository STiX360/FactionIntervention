# Faction Intervention Test Readiness

## Quick Test

Run Test-Faction-Intervention.cmd yourself. It starts a fresh isolated OpenMW 0.51.0
session in Seyda Neen using only Morrowind.esm and FactionInterventionTest.omwscripts.
The test manifest already includes the production player script. Do not enable
both manifests together. Close another running OpenMW game first.

The test supplies Divine Intervention, ALMSIVI Intervention, Mark, Recall, ten
scrolls of each Intervention, and a cast-on-use clothing item for each Intervention.
The actual item record IDs are printed in openmw.log. Fixtures use existing vanilla
records selected by effect and enchantment type. Both factions initially start as
nonmembers. Mysticism, Willpower, and Luck are raised to 100; magicka is supplied.
Test caps are 1 at faction rank 1 and 2 at rank 3. Promotion raises capacity only.
Version 0.2.0 adds two labelled native-script shrines and 500 gold; SHRINE-TEST.md
provides the focused renewal/recovery walkthrough. Use a fresh launcher session,
not a test save from an older fixture version.
Look for the test-kit-ready message and verify the supplies in the magic/inventory
windows before testing. If the message is absent, inspect openmw.log for Lua errors.

Default paths are the installed OpenMW 0.51.0 and Steam Morrowind directories.
Override using tools/start-test.ps1 -Engine 'C:\Path\openmw.exe' -GameData
'D:\Path\Data Files'. Use -PrepareOnly to write config without launching.
Settings, logs, and saves stay under this package's .runtime directory. Windowed
1280x720 and muted music are defaults on the first launch. Existing test settings
are preserved. Each launcher run starts a fresh session; load a test save explicitly
only for the save/load cases. Never use a regular playthrough save with the fixtures.

## Test Commands

Open the console with the console key and enter `luap` once. Then enter:

```lua
I.FactionInterventionTest.run('member')
```

Close the console briefly to let delayed API changes take effect. Open it again
and enter `I.FactionInterventionTest.status()` to display and log the current cell,
position, ranks, spent uses, and remaining uses. You stay in Lua mode until entering
`exit()`. Cast spells normally through the magic window and normal casting controls;
commands do not simulate casts or teleport outcomes.

| Command argument | Effect |
| --- | --- |
| `member` | Join both factions at rank 1 |
| `promote` | Join if necessary and set both faction ranks to 3 |
| `max-rank` | Join if necessary and set both factions to their highest rank |
| `demote` | Set both factions to rank 1 |
| `nonmember` | Leave both factions |
| `ready` | Refill magicka/fatigue and restore high casting stats |
| `fail` | Empty magicka to test insufficient-magicka refusal |
| `home` | Return to the starting test area and its shrines |
| `day` | Advance 24 hours of real in-game time for recovery testing |
| `three-days` | Advance 72 hours of real in-game time |
| `disease` / `blight` | Apply a vanilla affliction so its native cure can be tested |
| `diagnostics` | Display/log shrine sessions started, confirmed, cancelled, expired, and lacking a matching effect |

Commands affect only character setup. They do not reset spent uses or highest
observed ranks. Start a fresh launcher session to repeat the initial sequence.
All test helpers are excluded from the production manifest.

## Gameplay Acceptance

Use status before and after each case. Confirm native cell/position and magicka
as well as counters; a counter alone cannot establish whether teleportation happened.

| Case | Procedure | Expected result |
| --- | --- | --- |
| Nonmember | From the fresh scene, cast each ordinary Intervention | Refusal; zero spent; no cast, magicka loss, or cell/position change |
| Member | Run `member`; cast Divine once, then ALMSIVI once | Each teleports and spends exactly one use in its own faction |
| Exhaustion | Attempt both ordinary spells again | Refusal and no teleport; counters stay at one |
| Scroll | At exhausted budgets, use each supplied scroll | Normal teleport; only scroll inventory decreases; counters stay at one |
| Enchanted item | At exhausted budgets, use each supplied Intervention item | Normal teleport/charge use; no faction debit |
| Recall | Cast Mark, travel away using a scroll, cast Recall | Return to the Mark; counters unchanged |
| Promotion | After one spent use, run `promote`; inspect, then cast | Rank-3 cap is two; one spent use persists, exposing one more use; success exhausts it |
| Insufficient magicka | While a use remains, run `fail`; attempt each spell | Native failure; no teleport or debit. Run `ready` afterward |
| Failed probability roll | On disposable save, lower Mysticism/Willpower/Luck using native console and restore magicka; retry until an actual failure occurs | No debit on failure. High test stats must be restored before success tests |
| Demotion/rejoin | Run `demote`, then `nonmember`, then `member`, inspecting after each | No renewal at previously observed rank; spent counters persist |
| Save/load | Change rank caps, save, reload, inspect and cast | Caps, counters, and highest observed ranks persist; fixtures are not duplicated |
| Disabled | Turn Enabled off in Script Settings, attempt an exhausted ordinary Intervention | Native cast works; counter unchanged |
| Input | Repeat nonmember/exhausted cases with controller and repeated held/pressed Use | No exhausted teleport through any tested input path |
| Other travel | Use a travel door and ordinary transport | Native travel works; counters unchanged |
| Shrine renewal | Spend uses, run `home`, complete each shrine's blessing/restoration service | Corresponding faction fills to current cap; other faction unchanged; timer stops |
| Shrine cancellation | Decline the donation; also request a cure when healthy | No refill and no timer reset |
| Natural recovery | Spend two uses at rank 3; advance one day three times | None after days 1/2, one after day 3; another after day 6; timer stops at full |
| Teleport disabled | On a separate test save, disable native teleportation with allowance available | No teleport or debit; native-flag fix passed the user's rerun |
| Selection/animation | Change spell selection during casting; attempt a second spell during an existing animation | A release must identify the actual successful cast; attribution is currently unresolved |

The selection/animation fixes have passed the user's four-case rerun. The
skill-success proxy still cannot prove exact engine-level successful Intervention
identity. That limitation is documented in the standalone 0.2.0 release scope;
passing this checklist does not imply universal compatibility. Arcane Misfires and full modlist checks require
a separate explicitly configured test profile; this minimal harness does not load them.

## Optional Item Limits (0.3.0)

Use the updated test launcher on a disposable character. Enter `luap`, then
`I.FactionInterventionTest.run('promote')`; close the console briefly. Both factions
should have 2/2 uses. Save a full-capacity baseline.

1. In Script Settings > Faction Intervention, verify **Exempt scrolls and enchanted
   items** starts checked. Use a Divine scroll and ALMSIVI enchanted item: both
   should teleport without any faction debit. Reload the baseline.
2. Uncheck that setting. Use a Divine scroll, return using `run('home')`, then use
   Adusamsi's Ring. Divine should go 2/2 -> 1/2 -> 0/2; ALMSIVI remains 2/2.
3. At Divine 0/2, attempt another Divine scroll and ring use. Both must be refused
   before teleport or resource use: scroll count and ring charge must not decrease.
4. Repeat steps 2-3 using an ALMSIVI scroll and the Amulet of Almsivi Intervention.
5. Recheck exemptions while exhausted: the items should work again, without changing
   spent counters or resetting recovery. Ordinary spells should remain exhausted.
6. Reload the baseline, uncheck exemptions, then run `nonmember`. After closing the
   console, both types of Intervention item should be refused without resource use.
7. Reload the baseline, uncheck exemptions, save and reload. Verify the checkbox is
   still unchecked and the spent counters are unchanged.

For empty-charge failure, reload the baseline, uncheck exemptions, select an
Intervention enchanted item and set its charge to zero in Lua player console mode:

```lua
require('openmw.types').Item.itemData(require('openmw.types').Actor.getSelectedEnchantedItem(require('openmw.self'))).enchantmentCharge = 0
```

Close the console and attempt the item. Expect native insufficient-charge failure,
no teleport, no faction debit, and no new timer. Scrolls have no charge to empty.
For teleport restrictions, use the already-tested `Player.setTeleportingEnabled`
command with `false`, attempt a scroll and an item with available allowance, and
verify no debit. Restore the flag to `true` afterward. Native resource consumption
under a teleport restriction is engine behavior and is not rolled back by this mod.
Do not use god mode: consumption tracking cannot observe an unconsumed scroll.

Inspect with `I.FactionInterventionTest.status()` after each case. Returning home
never restores allowances; complete the appropriate shrine service to refill.

## Unlimited Allowances

Use a disposable character, with the mod enabled. In the Lua player console run:

```lua
I.FactionInterventionTest.run('max-rank')
```

Close the console briefly, then inspect `I.FactionInterventionTest.status()`.
Primate and Patriarch should default to 99 in settings; older saves retain their
previous caps, so set both to 99 manually if needed. Status should show
`remaining=unlimited` and `recoveryHours=off` for both factions.

1. Run `ready` as needed and successfully cast each Intervention at least seven
   times. Teleport normally; spent uses must not increase and no recovery timer starts.
   No usage messages should appear, even with Messages enabled. Complete each
   faction's shrine service too: native blessings still apply, without a mod refill message.
2. Uncheck item exemptions. Use each faction's scroll and enchanted item. Native
   scroll/charge consumption still applies; faction spent uses must not increase.
3. Save and reload. The 99 settings, spent counters, and unlimited status persist.
4. Set Primate's limit to 2. With no previously spent Divine uses, two successful
   casts consume those uses and the third is refused. Almsivi remains unlimited.
5. Set Primate back to 99. Divine works again without adding to the two spent uses.
6. Run `member`, close the console briefly, and set Layman's Divine limit to 99.
   Divine remains unlimited at the lowest rank; setting it to 3 exposes one use
   after the two earlier spent uses. Recovery starts afresh, without banked time.
7. Run `nonmember`, close the console briefly, and try both ordinary spells and
   limited items. Membership is still required even when a rank's limit is 99.

Return to a fresh test session afterward, or restore your test settings before
running earlier finite-allowance cases. Unlimited refers only to this mod's faction
budget, not native magicka, casting chance, charges, scroll inventory, or teleport flags.

## Automated Checks

These checks launch no game:

```powershell
python .\tests\verify_readiness.py
python .\tests\test_prototype.py
python .\tests\test_package.py
.\tools\start-test.ps1 -PrepareOnly
```

verify_readiness.py parses the vanilla ESM to check the spells, factions, exempt
items, shrine templates/scripts, then compiles all runtime scripts using the installed engine's lua51.dll.
test_prototype.py runs against the installed engine's lua51.dll and needs only
Python. These checks verify data availability, syntax, and mocked logic. The specific
user-reported engine outcomes are recorded in reports/manual-results.md.
No engine was launched by the agent during preparation.

## Results

Record results in reports/manual-results.md. Include engine version, kit readiness,
input device, each case's status output, before/after cell and position, magicka,
and relevant Lua errors from .runtime/manual-user-data/openmw.log. The checklist
starts untested; do not interpret automated passes as gameplay passes.
