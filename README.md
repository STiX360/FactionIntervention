# Faction Intervention for OpenMW

Version 0.3.0. Targets standalone OpenMW 0.51.0 with Morrowind.esm.
The default behavior was tested in-game for 0.2.0. The new optional item-limit mode
passes automated tests but still needs its in-game acceptance check.

Divine Intervention and ALMSIVI Intervention have renewable, faction-rank-based
allowances. Imperial Cult rank governs Divine; Tribunal Temple rank governs ALMSIVI.
No ESP, MWSE, or bridge dependency is required.

## Rules

Nonmembers cannot cast the corresponding ordinary Intervention spell. Membership
ranks 1 through 10 default to 1, 1, 2, 2, 3, 3, 4, 4, 5, unlimited uses per faction.
Each rank's allowance is configurable in Script Settings: 0 disables its allowance,
1-98 sets a finite maximum, and **99 means unlimited**. Primate and Patriarch default
to 99; any lower rank can also be configured for unlimited use.
Existing saved settings are preserved: set the highest ranks to 99 or reset their
settings groups if updating a save that previously had finite highest-rank limits.

- Promotion increases maximum capacity without erasing spent uses.
- Each faction restores one use every three in-game days, independently.
- Further casts do not restart an active recovery timer. At full capacity it stops.
- Unlimited casts do not add spent uses or need recovery. Earlier spent uses remain
  preserved; returning to a finite allowance resumes recovery with a fresh timer.
- Unlimited ranks produce no usage or restoration messages; native casting works
  quietly. Finite ranks still follow the Messages setting.
- Resting/waiting counts; time spent at full capacity cannot be banked.
- Completed supported shrine services refill the corresponding faction to its
  current maximum. Free services at higher ranks qualify too.
- Opening or cancelling a shrine menu does not refill uses. A cure requires an
  actual matching effect; requesting one while healthy does not qualify.
- Scrolls and enchanted items are exempt by default. Turn off **Exempt scrolls and
  enchanted items** in Script Settings to make their Intervention uses require
  membership and consume the same faction allowance as ordinary spells.
- Recall, powers, and spells/enchantments containing Recall are not limited.
- Failed casts and native teleport-disabled casts do not consume uses.
- Counters, recovery progress, and settings persist through save/load.

Demotion/rejoining does not reset spent uses. With no membership or zero capacity,
recovery progress is discarded rather than banked. The mod does not change native
teleport restrictions, destinations, shrine prices, or vanilla shrine scripts.
The item-exemption setting is saved with your character. Existing saves default to
exemptions enabled; changing the toggle does not reset allowances or recovery timers.
Only manually cast scrolls and cast-on-use enchantments can be limited. Constant
effects, cast-on-strike enchantments, and non-Intervention items are unaffected.

## Installation

1. Extract the release ZIP into its own directory.
2. Add that directory as a data directory in the OpenMW launcher.
3. Enable `FactionIntervention.omwscripts` in the content list.
4. Configure allowances under Script Settings > Faction Intervention.

Back up your save before adding or updating any scripted mod. Older OpenMW versions
are not supported; other engine versions have not been validated for this release.
Install only the production manifest. `FactionInterventionTest.omwscripts`, if
obtained separately in the development package, is not for normal playthroughs.

## Compatibility

The 0.2.0 standalone gameplay checks passed on OpenMW 0.51.0. Compatibility with other mods is
not guaranteed. The following are risk areas, not a list of confirmed conflicts:

- **Casting animation replacers:** changes that rename/remove the `spellcast`
  animation group, skip the casting animation, or alter its timing/cancellation or
  release events may cause missed or incorrect usage deductions. Visual-only
  replacements retaining the native casting behavior are not known conflicts.
- **Casting, input, or skill-progression overhauls:** mods that change cast initiation,
  successful Mysticism notifications, or suppress/reroute spell effects may affect
  accounting. Arcane Misfires and similar casting mods have not been tested.
- **Other Intervention limiters:** overlapping restrictions or counters can conflict.
  Use one Intervention allowance system at a time.
- **Shrine overhauls:** standard native services are observed without replacing their
  scripts. Replaced menu scripts, different blessing spells, or altered effect timing
  may prevent renewal. New or quest/pilgrimage shrines are not automatically supported.
- **Custom spells:** spells combining Divine and ALMSIVI Intervention are unsupported;
  currently only the first Intervention effect determines the charged faction.
- **Faction or total-conversion overhauls:** the mod expects the vanilla `imperial cult`
  and `temple` faction IDs and their normal rank structure.

Usage accounting correlates the spell chosen at cast initiation, the native casting
animation, a successful Mysticism notification, and the teleport-enabled flag. It
does not receive an engine event proving the exact spell's completed teleport.
Mods that alter those signals are the most likely compatibility problem area.
With item exemptions disabled, cast-on-use items use the native successful Enchant
notification and scrolls use a decrease in the selected scroll record's inventory
count during a pending cast. Mods that remove/add those scrolls during casting or
alter item-use notifications can affect accounting. God-mode scroll casting, which
does not consume a scroll, is not supported by consumption tracking.

Supported shrine scripts are `shrineImperial`, `shrineTemple`, `shrineVeloth`,
`shrineVivecFury`, `shrineVivecHumility`, and `shrineVivecMystery`. The Imperial and
Tribunal fixtures were tested in-game, including shared disease/blight cures.
The other supported script layouts were checked against vanilla data, not individually
tested in-game. Arbitrary replacement scripts are unsupported.

## Reporting Issues

Include your OpenMW version, mod version, relevant casting/animation/shrine mods,
the spell or item used, faction rank, and whether teleportation actually occurred.
For renewal problems, include the shrine and service selected. Attach the relevant
`openmw.log` entries and reproducible steps. If possible, check whether the same issue
occurs with only this mod and Morrowind.esm; do not disable mods on your main save
just to test a report. Use a separate profile and disposable character instead.

## Credits

Inspired by the faction restrictions described in
[Merlord's Limited Intervention](https://www.nexusmods.com/morrowind/mods/46687).
Independently written for OpenMW; no Merlord code, assets, or dialogue are included.
The defaults and renewal rules are this mod's own design, not a claim of exact parity.

## Development

The separate development/test package includes `TESTING.md`, `SHRINE-TEST.md`, an
isolated launcher, and validation reports. Automated tests use the installed engine's
Lua 5.1 runtime. Run `python tests/test_prototype.py` and
`python tests/verify_readiness.py` from the development checkout.
Run `python tools/package.py` for the production ZIP, or add `--test` for the
development ZIP. Neither archive includes saves, game data, or external dependencies.

In the source checkout, release automation and one-time Nexus setup are documented in
[NEXUS-PUBLISHING.md](NEXUS-PUBLISHING.md). Push a matching `vX.Y.Z` tag after
committing and pushing to `main` to publish the production ZIP to GitHub Releases
and, when configured, Nexus. Ordinary commits only run validation.
