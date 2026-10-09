# Changelog

## 0.3.0

- Rank allowances set to 99 now grant unlimited faction uses. Primate and Patriarch
  default to 99; all ranks remain configurable. Existing saved limits are preserved.
- Settings are grouped by Intervention/faction and use vanilla rank titles.
- Unlimited ranks no longer display usage or shrine-restoration messages.
- Added the default-on **Exempt scrolls and enchanted items** Script Settings toggle.
- Disabling exemptions makes Intervention scrolls and cast-on-use items require
  membership and consume the corresponding faction's ordinary allowance.
- The toggle persists with saves without resetting spent uses or recovery timers.
- Recall, powers, constant effects, and cast-on-strike enchantments remain unaffected.
- Added regression coverage for item accounting, failures, and teleport restrictions.

Targets standalone OpenMW 0.51.0. Default behavior passed the 0.2.0 in-game checks;
the optional item-limit mode passes automated tests but awaits in-game acceptance.
Casting/animation/shrine overhauls are unverified; see the README compatibility notes.

## 0.2.0

- Renewable faction-rank-based Divine and ALMSIVI Intervention allowances.
- Supported native shrine services fully renew the corresponding allowance.
- Independent one-use-per-three-day recovery, preserved through save/load.
- Corrected disabled-teleport deductions and spell-switch accounting.
- Standalone gameplay checks passed on OpenMW 0.51.0.
