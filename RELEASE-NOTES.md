# Faction Intervention 0.3.0

## Changes in 0.3.0

- A rank allowance of **99** now means unlimited faction uses. Primate and Patriarch
  default to 99; lower ranks can also be made unlimited. Existing saved limits remain
  unchanged, so set the highest ranks to 99 when updating an older save if desired.
- Settings now separate General, Divine/Imperial Cult, and Almsivi/Tribunal Temple,
  with named ranks and an explanation of the unlimited value.
- Added **Exempt scrolls and enchanted items** to Script Settings, enabled by default.
- Turn it off to require faction membership and share the ordinary Intervention
  allowance with scrolls and cast-on-use enchanted items.
- The setting persists with your save. Saves without it retain the original exemption.
- Changing the toggle never resets spent uses or recovery progress.
- Empty-charge item failures and native teleport restrictions do not cause a debit.
- Recall, constant effects, cast-on-strike enchantments, and other items remain unaffected.

The item-limit mode and configurable unlimited allowances have automated regression
coverage. Their complete in-game acceptance checks remain pending. The standalone gameplay results
below describe the 0.2.0 baseline, not a new claim that item limits were tested in-game.
Consumption-based scroll accounting is not compatible with god-mode scroll casts
that do not consume inventory, and can be affected by other mods changing inventory
during the pending cast. See README.md for the complete compatibility boundaries.

## Previous Release: 0.2.0

## Release Scope

Standalone OpenMW 0.51.0 with Morrowind.esm. Other mod combinations are unverified;
compatibility reports will be handled as they arrive. This is not a claim of universal
compatibility or a verified engine-level successful-teleport hook.

## Features

- Separate rank-based Divine and ALMSIVI Intervention allowances.
- Rank-specific Script Settings, with capacity increases on promotion.
- Full renewal from supported native shrine services, including free services.
- Independent one-use-per-three-day recovery, preserved through save/load.
- Default scroll and enchanted-item exemptions; Recall and power exemptions.
- No ESP, MWSE, bridge, vanilla-record edits, or bundled game assets.

## Validation

The author reported standalone in-game checks passing for renewal, disease/blight
cures, free shrine services, promotion, timed recovery, save/load, insufficient
magicka, failed casting rolls, scroll/item exemptions, disabled teleportation,
and all four spell-selection switching cases. Thirty automated regression tests
also pass. An extra cast-button press during an existing animation was not tested
in-game. Full modlist compatibility was not tested.

The test-fixture save-location serialization fault, disabled-teleport debit, and
spell-switch missed debit found during testing were corrected before this release.
The public ZIP excludes the character-changing test helpers and launcher.

## Compatibility Notice

Casting overhauls and animation replacements that change native `spellcast` behavior
are the primary usage-accounting risk. Visual-only animation replacements are not
known conflicts. Other Intervention limiters should not be combined with this mod.
Modified shrine scripts/blessings may prevent renewal. Mixed Divine/ALMSIVI spells
are unsupported. Arcane Misfires compatibility has not been tested.

See README.md for installation, detailed compatibility boundaries, and issue-report
requirements. Back up your save before installing or updating.
