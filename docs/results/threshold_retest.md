# Re-test of the recent-change threshold, with the persistence rule

Run on 900 synthetic workbooks, 15 Nov 2026. Command: `python scripts/threshold_check.py <folder> 1.5 1.0 0.8`.
The data is synthetic, so this shows how the rule behaves, not clinical accuracy.

## What changed in the code
- **Persistence rule.** The latest 14 days are compared with the 90 days before them as before, but the change must now also show in *each* of the latest two weeks: same direction, and at least 75% of the threshold (`RECENT_PERSIST_SHARE` in `pranapulse/signals.py`). A one-week spike is no longer flagged.
- **Larger minimum change for daily steps.** 600 to 1,000 steps (`min_abs` for steps in `pranapulse/signals.py`).

## Patients flagged by the recent-change check (of 900)

| Threshold | Before persistence | With persistence |
|---|---|---|
| 1.5 (earlier setting) | 0 | 0 |
| 1.0 | 2 | 2 |
| 0.8 | 26 | 17 |

Trying other shares at 0.8: 50% flags 26, 75% flags 17, 100% flags 9. We use 75%.

## Whole-dataset findings (validation run)

| Setting | People with a finding | Flagged sections |
|---|---|---|
| Threshold 1.5, before and after | 85 of 900 (9%) | 89 (62 metabolic, 21 women's health, 6 cardiovascular) |
| Threshold 0.8, before | 110 of 900 (12%) | not recorded |
| Threshold 0.8, with persistence | 101 of 900 (11%) | not recorded |

At 1.5 the counts do not change.

## Decision (15 Nov 2026): the recent check now uses 0.8
`RECENT_MIN_EFFECT` in `pranapulse/signals.py` is now **0.8**, the same size as the first-versus-last check, with the persistence rule kept. At 1.5 the recent check flagged nobody, so it never showed anything.
| Setting | People with a finding | Flagged sections |
|---|---|---|
| Recent check at 1.5 (before) | 85 of 900 (9%) | 89 (62 metabolic, 21 women's health, 6 cardiovascular) |
| Recent check at 0.8 with the persistence rule (now) | 101 of 900 (11%) | 106 (62 metabolic, 21 women's health, 23 cardiovascular) |
- Metabolic and women's health do not change. Cardiovascular goes from 6 to 23 sections.
- Agreement with the recorded history for cardiovascular is weak at both settings (1% vs 1% at 1.5, 3% vs 2% at 0.8). See `history_consistency.md`.
- This is a choice, not a proven improvement: there are no outcome labels to show that 0.8 is more accurate. To be confirmed with the partner.

## Steps minimum
People with a steps change between the first and last 90 days: 142 at 600 steps, 134 at 1,000, 103 at 1,500. We use 1,000.

## A correction
Earlier documents (`model-comparison.md`, `three-approaches.md`, `meeting-3-plan.md`) say 28 patients at 0.8. That run was before the first and last windows were made exactly 90 days (31 Oct). With the current code the figure is **26**, which is the baseline for this table.
