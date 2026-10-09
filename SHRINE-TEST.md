# Shrine and Recovery Walkthrough (0.2.0)

Close OpenMW, then double-click Test-Faction-Intervention.cmd for a fresh test.
Do not load an older test save. In Seyda Neen, look nearby for two labelled objects:
FI: Imperial altar (Divine) and FI: Tribunal shrine (ALMSIVI). Spells, enchanted
items, scrolls, and 500 gold are supplied. Their menus use unmodified vanilla scripts.

## Commands

Open the console and enter `luap` once. Then use:

```lua
I.FactionInterventionTest.run('member')
```

Close the console for a moment after each command. This applies queued changes.
Open it again to inspect:

```lua
I.FactionInterventionTest.status()
```

Status logs/displays both ranks, spent/remaining uses, and hours until recovery.
Other run arguments used below are `home`, `promote`, `day`, `three-days`,
`disease`, `blight`, and `diagnostics`. Native casts must still be performed normally.

## Paid Shrine Renewal

1. Run `member`. Cast ordinary Divine Intervention once and ALMSIVI once.
   Status should show used=1, remaining=0 for both, with running recovery timers.
2. Run `home` to return to the test shrines. Returning home never refills uses.
3. Activate the Imperial altar and decline its donation. No uses should return.
4. Activate it again, accept its normal donation, and select Restore Attributes.
   Wait a few gameplay seconds. Divine should show used=0, remaining=1 and
   recoveryHours=off. ALMSIVI must still be spent. Check that native gold cost applies.
5. Activate the Tribunal shrine, accept its donation, and select Lady's Grace.
   ALMSIVI should now show used=0, remaining=1 and recoveryHours=off.
6. Spend ALMSIVI again, return home, and select Lady's Grace again while its earlier
   blessing is still active. This fresh service must refill again; merely retaining
   the old blessing must never refill a subsequently spent use.

If a service works natively but does not refill, run `diagnostics` and report its
displayed counts. `noEffect` means completion was seen but no fresh matching active
spell was observable. `started=0` means activation was not detected. Check openmw.log
for errors and FI shrine trace lines. This is an engine-observation prototype.

## Free Services and Shared Cures

1. Run `promote`: both factions become rank 3 with cap 2 and free native services.
   Promotion must preserve already spent uses, not refill them.
2. Exhaust the two-use capacities through ordinary casts, returning with `home`.
3. Receive the Imperial restoration service and Tribunal Lady's Grace again.
   Each should refill its own faction even though no gold is charged.
4. Spend one Divine use, return home, and ask the Imperial altar to cure a disease
   when healthy. Its refusal must not restore Divine or restart its timer.
5. Run `disease`, close the console, and use that altar's Cure Disease service.
   Confirm the affliction is removed and only Divine refills.
6. Repeat using the Tribunal shrine after spending one ALMSIVI use. The same cure
   spell must now restore ALMSIVI instead. Repeat with `blight` and Cure Blight.

Instant cure visibility is specifically under test. Do not count successful native
cure alone as a mod pass: the correct allowance must refill too.

## Three-Day Recovery

1. At rank 3, exhaust both capacities again. Check used=2, remaining=0.
2. Run `day` twice, closing the console after each. No use should recover yet.
3. Run `day` once more: each should recover one use. Status should show used=1,
   remaining=1, with a fresh roughly 72-hour timer.
4. Run `three-days`: both should become full, with recoveryHours=off.
5. Advance another three days while full, then spend one use. Its new timer should
   start at roughly 72 hours; previous full-capacity time must not be banked.
6. Refill at the shrine while that timer runs. It must stop immediately.
7. For persistence, spend a use, advance one day, save and load that new test save.
   Roughly 48 recovery hours should remain. Two more days should restore it.

If testing after the 2026-10-09 save-location fix, quit and relaunch the test launcher
to load the corrected scripts. Use its fresh session, run `promote`, and repeat step 7
with a new save. The earlier faulty save reset membership and recovery progress;
it is not a valid persistence baseline.

To check casts do not postpone recovery: spend one use at rank 3, advance one day,
spend the second use, then advance two more days. One use should recover three days
after the first cast, not three days after the second.

Record failures with step number, status, diagnostic counts, and relevant log lines
in reports/manual-results.md. This test changes only the disposable profile. No
engine test was run during preparation; the earlier successful-teleport attribution
limitations remain separate from the renewal detector.
