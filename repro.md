# Reproducibility probe — Haiku, two metrics

Goal: see whether schema variant correlates with a deterministically-measurable defect rate. Two metrics tried. The first (narrative blockers) found a flat ~2–3% across variants. The second (per-encounter weakness reachability) found a clean **10–15× separation** between the schema variants the autoregressive-order thesis predicts will fail and the ones it predicts will work.

Corpus: 24 normalized batches (`results/normalized/minimal_*.json`), 6 variants × 4 batches × 16 cases = 384 levels. Judge: Haiku 4.5, one subagent per file, 24 in parallel.

---

## Metric 2 — Per-encounter weakness reachability (the result)

For each encounter `i` in each level, does anything in the player's inventory at that point (`{player_weapon} ∪ {pickups from encounters 0..i-1}`) satisfy `encounter[i].enemy.weakness`? Haiku decides semantically (e.g. "Flame Burst Staff" satisfies weakness "Flame Burst") but not over-permissively (e.g. uncharged "Obsidian Spike" does not satisfy weakness "Charged Obsidian Spike"). One binary verdict per encounter, 48 per file, 192 per variant.

### Headline

| Variant | files | breaks | encounters | rate | vs baseline |
|---|---:|---:|---:|---:|---:|
| **`append_order`** (3) | 4 | 14 | 192 | **7.3%** | **14×** |
| **`flat_alpha`** (1) | 4 | 9 | 192 | **4.7%** | **9×** |
| `alpha_nested` (5) | 4 | 3 | 192 | 1.6% | 3× |
| `grouped_by_type` (2) | 4 | 1 | 192 | 0.5% | 1× |
| `ui_contract` (4) | 4 | 1 | 192 | 0.5% | 1× |
| `nested_narrative` (6) | 4 | 1 | 192 | 0.5% | 1× |

Three variants tie at the floor (~0.5% — basically Haiku judgment noise). The two variants the thesis predicts will fail are an order of magnitude noisier. `alpha_nested` (alphabetical *within* objects, but objects in narrative order) lands sensibly between full alphabetical and the good orderings.

### The defect this metric catches

The model commits `encounter[i].enemy.weakness` to a specific item name and then later writes a pickup whose name doesn't match it. The player walks into the encounter without anything in inventory that satisfies the weakness. This is the autoregressive-order failure shape the thesis predicts: in flat_alpha, fields appear in `encounter_0_enemy_weakness, encounter_0_hazard, ..., encounter_0_pickup_name` order, so the weakness gets written before the pickup that's supposed to satisfy it, and the model has to *guess forward*. In nested_narrative the pickup is decided in the same encounter object before the next encounter's enemy is named, so the model can look back.

### Examples (verified by re-reading the file)

**`append_order` — minimal_3_1, `horror_eerie_alchemist_hard`:** all 3 encounters break.
- enc 0 weakness `Acid Vial`, inventory `["Alchemical Transmutation Staff"]` — staff doesn't produce acid vials.
- enc 1 weakness `Concentrated Catalyst`, inventory has `Alchemical Acid Vial` instead — different item.
- enc 2 weakness `Explosive Catalyst`, inventory has `Concentrated Solvent` — different item.
The model wrote a "Concentrated Catalyst" weakness, then later wrote a "Concentrated Solvent" pickup. No matching item ever arrives.

**`append_order` — minimal_3_2, `jungle_whimsical_alchemist_easy`:** all 3 encounters break, same pattern.

**`flat_alpha` — minimal_1_2, `jungle_desolate_berserker_brutal`:** enc 2 weakness `Charged Obsidian Spike`; inventory has uncharged `Obsidian Spike` and `Storm Essence`. The charged spike only appears as enc 2's own pickup, which is unavailable during enc 2.

**`flat_alpha` — minimal_1_2, `jungle_mysterious_ranger_medium`:** enc 1 weakness `Corrosive Blade`; inventory has `Venom Gland` (effect: "adds corrosive damage to blade"). Borderline — Haiku said no because the pickup *describes adding* corrosive damage, not *being* the corrosive blade. Reasonable.

### Caveats

- Haiku's per-encounter judgments still have some noise — some "Stormcaller Gauntlet vs Chain Lightning" calls could go either way. But the variant-level separation is so large (14× between the worst and the best) that judgment noise can't explain it.
- N is still small (192 encounter checks per variant, ~3 batches with breaks for `append_order`). The ranking is stable but the exact rates (7.3% vs 4.7%) shouldn't be read as precise.
- The metric checks whether the inventory *literally* contains an item that satisfies the weakness. Cases where the player has *no* matching item but the trigger handwaves a workaround don't get flagged.

---

## Metric 1 — Narrative blockers (the earlier null result)

For each level, does the level's own description allow the player to reach and defeat the boss? Flag levels where a `trigger` says "the path is sealed," "the corpse blocks the gate," etc.

| Variant | n | Real defects (after FP filter) | Rate |
|---|---:|---:|---:|
| `flat_alpha` | 64 | 2 | 3.1% |
| `grouped_by_type` | 64 | 2 | 3.1% |
| `append_order` | 64 | 0–1 | 0–1.6% |
| `ui_contract` | 64 | 0 | 0% |
| `alpha_nested` | 64 | 2 | 3.1% |
| `nested_narrative` | 64 | 2 | 3.1% |

No ordering effect. The canonical eel sits here in flat_alpha (`underwater_ominous_necromancer_hard`, trigger: "Eel carcass blocks the path to the ancient gate"), but every variant has 0–2 narrative blockers; the differences are noise.

The narrative-blocker class is real but rare across the corpus (~2% per variant). The lesson: **the eel is a memorable instance of a much broader autoregressive-ordering defect class**, but the eel-shape itself doesn't have enough volume to discriminate variants. The reachability metric does.

---

## Methodology notes

Things that turned out to matter for Haiku reliability:

- **"Do not write or run code"** — without it Haiku writes Python to mechanically string-compare fields. Triggers get treated as flavor text, semantic judgments are skipped.
- **Explicit inventory specification per encounter** — Haiku confuses "the pickup from encounter i" with "the pickup the player has during encounter i" if you don't pin it down.
- **Binary outputs with required quotes** — making Haiku quote the breaking text or the satisfying item makes spot-checking trivial.
- **Per-batch variance** — one batch out of 24 (minimal_1_0 in the narrative probe) invented a "pickups are consumable" rule despite the prompt explicitly saying they aren't. The other 23 obeyed. Cross-batch variance is the dominant failure mode at this model size, not per-case judgment.

## What this says about the experiment

The autoregressive-schema thesis predicts that schemas committing field A before field A's dependency (B) will fail more often, because the model has to write A without knowing what B will be. Per-encounter weakness reachability measures exactly that: `enemy.weakness` is committed before the prior encounter's `pickup.name` in flat_alpha and append_order, but after it in nested_narrative.

The result: variants where the dependency direction is *backward* (flat_alpha 4.7%, append_order 7.3%) have ~10× more chain breaks than variants where the dependency is *forward* (nested_narrative, ui_contract, grouped_by_type at 0.5%). Not a subtle effect. The original Likert judge was directionally right; it just wasn't measuring what it claimed to be measuring.

Next steps to make this airtight:
1. Run the same reachability check on the GA model corpus (`gamin_*`) and the thinking-budget corpus (`low/medium/high_*`). Each adds another 24 files per condition. With n≈576 encounter checks per variant per condition, sub-1% differences should resolve cleanly.
2. Add a sanity check: re-run the same prompt on 2–3 files with different Haiku invocations to estimate per-case variance independently of cross-batch variance.
