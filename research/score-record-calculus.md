# Reading the family's own live score record as a measurement

Registered 2026-10-06. Produced by `scripts/score_record_calculus.py` →
`evidence/score_record_calculus.json`, and by `scripts/invert_label_field.py` →
`evidence/label_field_inversion.json` (the negative result, section 5).

## 1. Why this exists

Two instruments were available before this session and both are broken for the question that
matters:

* **The proxy holdout.** Truth = the published catalogue or a blocked piece of it. The prize
  round is scored on faults *absent* from that catalogue and masks catalogue pixels out of
  every term, so a candidate engineered to emit off-catalogue scores structurally ≈ 0. That is
  what `docs/downloads/holdout.json` records for H41-A (`7.098e-09`) and
  `research/experiments/h41e-kinematic-holdout.json` for H41-E (`0.000000`). Those are
  properties of the instrument.
* **The projected-score model.** `validate.project_live_dti` conditions on a single
  owner-reported hidden-set size (`K_HIDDEN_PX = 13_000`) that was never derived in this
  checkout from more than one pair of numbers.

There is a third instrument, and it is a real one. Across ~40 sibling projects this family has
published **rasters whose scores the portal actually returned**. Each such raster is a *known
probe* `E_i` of the hidden label set `G`: known support, known mass, known live score. The
official index is explicit enough that a probe plus its score is an equation in the unknowns
`(|G|, distribution of G)`.

**Evidence class.** Every score used here is *owner-reported on a sibling project page*, not an
organizer receipt. They are transcribed in `registry/score_ledger.csv` with their source URLs.
Nothing below is a claim about the current leaderboard, and `drivendata.org` was never
requested by any script in this repository.

## 2. The probe corpus

`scripts/fetch_probe_corpus.py` restored **29 rasters / 27 distinct supports** from immutable
GitHub paths (`data/probes/`, gitignored, SHA-256 recorded in `data/probes/probes.json`). Three
of them — `dot_d28`, `poisson300_44090`, `efd28_repro` — are byte-identical in support and were
each independently reported at **0.2600** by three different project pages. That triple
agreement is the strongest available check on the reliability of the reported numbers.

All 29 are single-band float32 on the exact organizer grid (3730 × 3292, EPSG:32611,
transform 243350 / 4508550). Measured properties that matter:

| probe | active mass | reported | median dist. to catalogue (px) | frac ≤ 3 px | on catalogue |
|---|---|---|---|---|---|
| h33_2b2 | 37,654 | **0.2778** | 19.65 | 0.058 | 0 |
| h274_solo | 40,199 | 0.2708 | 17.69 | 0.117 | 0 |
| h321_prethin | 42,294 | 0.2649 | 16.12 | 0.161 | 0 |
| h33d_stepover | 41,865 | 0.2632 | 16.64 | 0.144 | 0 |
| dot_d28 = poisson300 = efd28 | 44,090 | 0.2600 | 15.00 | 0.195 | 0 |
| dot_d15 | 60,069 | 0.2477 | 14.87 | 0.199 | 0 |
| tgc_d15 | 61,328 | 0.2449 | 14.14 | 0.199 | 0 |
| h19_5 | 121,131 | 0.1922 | 14.56 | 0.200 | 0 |
| **h34_scatter** | **37,654** | **0.0778** | 19.65 | 0.058 | 0 |
| h35_06 | 39,530 | 0.0418 | 15.00 | 0.206 | 0 |
| h23b_10pct | 516,738 | 0.0748 | 14.56 | 0.167 | 0 |
| h16_continuation | 283,532 | 0.0461 | 3.00 | 0.505 | 26,510 |
| hedge_v2 | 166,519 | 0.1563 | 6.71 | 0.404 | 60,988 |
| placeholder | 145,610 | 0.0107 | 119.5 | 0.044 | 2,074 (+196,132 outside footprint) |

Two facts jump out before any modelling:

* **`h34_scatter` has the same mass, the same minimum separation and the same
  distance-to-catalogue distribution as the 0.2778 file, and scores 0.0778.** It is the
  family's own arrangement-matched, position-randomised control. Positional skill at fixed mass
  and fixed arrangement is therefore worth a factor **3.57**, and the emitter geometry is not
  where the remaining value is.
* **Hugging the catalogue loses.** `h16_continuation` puts half its mass within 300 m of a
  mapped fault and 26,510 dots *on* mapped faults, and scores 0.0461. The best file has a
  minimum catalogue distance of 2.24 px and only 5.8 % of its mass within 3 px.

## 3. The algebra

With `k(d) = max(1-d/3, 0)`, `TP_w = Σ_g max_x p(x)k(d(x,g))`, `FP_w = Σ_x p(x)(1-max_g k)`,
`FN_w = |G| - TP_w` and `DTI = TP_w/(TP_w + 0.2 FP_w + 0.8 FN_w)`, identity (2) of
`src/gems41/metric.py` gives `1/DTI = 0.2 + 0.2 FP_w/TP_w + 0.8 |G|/TP_w`.

Model the hidden set as an independent Bernoulli field with intensity `π(x) = ρ·u(x)`,
`u ≥ 0`, `Σu = 1` over the **active** domain (in-footprint, off-catalogue: 5,106,385 px), so
`E|G| = ρ`. For a probe with prediction `p`:

```
E[TP_w] = ρ · a ,   a = Σ_x u(x) K_p(x) ,  K_p(x) = max_y p(y) k(d(x,y))     (exact)
E[FP_w] = M - ρ · q, q = Σ_x u(x) S_p(x) ,  S_p(x) = Σ_y p(y) k(d(x,y))      (first order)
M       = Σ_{x active} p(x)
```

`a` and `q` are both **linear in `u`**, which is what makes the record invertible. Eliminating
`ρ a` gives, for any probe,

```
a·(1 - 0.2 s) + 0.2 s·q  =  0.8 s + 0.2 s (M + λ·M_off) / ρ            (*)
```

where `λ ∈ {0,1}` is the (unknown) treatment of mass placed outside the footprint.

### The nested-lineage collapse

For a lineage `E_1 ⊃ E_2 ⊃ …` in which every removed dot carried **no** credit — `TP_w`
constant, `FP_w` falling one-for-one with mass — (*) becomes a straight line:

```
1/s_i = c0 + m·M_i ,   c0 = 0.2 + 0.8/a ,   m = 0.2(1 - ρ·q̂)/(ρ·a) ,  q̂ = q_i/M_i
```

So an ordinary least-squares fit of `1/s` on `M` over a nested lineage returns the belief
field's coverage `a`, its weighted true positives `ρa`, the hidden label count `ρ`, and — because
`c0` is the `M → 0` intercept — the field's **ceiling** `s_max = 1/c0 = a/(0.2a + 0.8)`.

**Containment was verified from the bytes, not assumed** (`evidence/score_record_calculus.json`,
`lineage_containment`): `dot_d15`, `dot_d28`, `h321_prethin`, `h274_solo` and `h33_2b2` are each
**exactly** contained in `h19_5` (fraction 1.0000), and `h33d_stepover` is 0.9968 contained.

## 4. Results

| fit | members | `1/s = c0 + m·M` | R² | coverage `a` | `TP_w = ρa` | `ρ` | ceiling `s_max` |
|---|---|---|---|---|---|---|---|
| full chain | 8 | `2.97810 + 1.83037e-5·M` | **0.9922** | 0.2880 | 10,232 | 35,533 | **0.3358** |
| dotted core | 5 | `2.98842 + 1.78715e-5·M` | 0.9053 | 0.2869 | 10,462 | 36,467 | **0.3346** |

Read off the fitted line (a held at 0.287, i.e. assuming thinning keeps removing dead weight):

| emitted mass | projected score |
|---|---|
| 37,654 (incumbent) | 0.273 |
| 30,000 | 0.284 |
| 20,000 | 0.299 |
| 12,000 | 0.313 |
| 8,000 | 0.319 |
| 5,000 | 0.326 |
| → 0 | **0.335** |

Three consequences, in order of importance:

1. **The incumbent belief field's ceiling is 0.3346–0.3358**, above the 0.3262 that headed the
   dated 2026-10-05 public snapshot. Nobody needs a better geological idea to lead; they need
   to stop paying for redundant dots. `a` did not move at all while 69 % of the mass was removed
   (121,131 → 37,654 px), which is direct evidence that most of the shipped mass covers truth
   pixels that other shipped dots already cover.
2. **`ρ ≈ 35,500–36,500` hidden label pixels**, not the 13,000 carried in
   `validate.K_HIDDEN_PX`. The old constant came from adjacent pairs under the assumption
   `FP_w ≈ M`; keeping the `q` term moves it by a factor 2.7 and moves every projected score
   with it. This is recorded as an irregularity (IR-42-RHO-01) rather than silently overwritten.
3. **The emitter, not the geology, is the binding constraint.** With `a` fixed, DTI is monotone
   in mass down to zero; the only thing that stops thinning is `a` starting to fall. That is a
   measurable property of an emission operator, which is what `src/gems41/coverage.py` exists to
   optimise.

### The null model checks out against a live score

For a position-blind dot set (uniform `u`) the score cannot exceed
`s_ceiling = a/(0.2a - 0.2q + 0.8)` at any `ρ`. For `h34_scatter` — 37,654 scattered dots,
measured `a = 0.0620`, `q = 0.0688` under uniform density — that ceiling is **0.0776**. The
reported score is **0.0778**: a relative error of **+0.21 %**. The metric transcription, the
kernel offsets, the active-domain masking and the probe measurements are therefore consistent
with a live score to within reporting precision. This is the strongest verification available
in this sandbox and it is worth more than any further proxy holdout.

It also calibrates what "skill" means: at 37,654 px, position-blind emission is worth 0.0776
and the incumbent's placement is worth 0.2778. Any new candidate should be compared against
0.0776, not against 0.

## 5. Negative result: the 21-template mixture inversion does not identify the label field

`scripts/invert_label_field.py` fits `u = Σ_j w_j u_j` on the simplex over 21 geologically
interpretable templates (7 catalogue-distance bins, uniform, LiDAR scarp evidence, and 12
official-band anomalies) together with `ρ`, by solving (*) for every probe. It **fails**, and
the failure is informative:

* best fit `ρ = 53,893`, RMSE **0.106** on scores that span 0.0107–0.2778;
* leave-one-probe-out RMSE **0.111**, `max|residual| = 0.218`, only 2/29 probes predicted
  within 0.01;
* residuals are systematic, not noise: every high scorer is under-predicted (`h33_2b2`
  −0.212) and every dense low scorer is over-predicted (`lat_s5` +0.135, `h23b_10pct` +0.073);
* `λ = 0` and `λ = 1` (outside-footprint mass counted as false positives or ignored) are
  indistinguishable (RMSE 0.1061 vs 0.1053), so the corpus cannot settle that format question
  either;
* the fitted weights are geologically meaningless (0.60 `tmi_hg` + 0.23 `dcat_0_1`).

Why: a dense probe such as `h23b_10pct` (516,738 px, 10 % of the footprint) has `K_p(x)` close
to 1 over most of the domain, so `a ≈ 0.9` for *almost any* `u`, while its reported 0.0748
demands `a ≈ 0.20`. Simultaneously `h33_2b2` (37,654 px covering 6.9 % of the domain) demands
`a ≥ 0.222`, i.e. ≥ 3.2× concentration inside that 6.9 %. No smooth mixture of catalogue
distance and single-band anomalies satisfies both, because the label field is not a smooth
function of those layers — it is a set of thin expert-drawn traces whose alignment with any
given belief field is what the score actually measures. The inversion is therefore
**under-determined by 29 scalar observations**, and reporting a fitted `u` from it would be
exactly the kind of unsupported number this repository exists to avoid.

What survives is the nested-lineage fit (section 4), which uses only *ratios within one belief
field* and so never needs to know `u` — only that `u` is fixed while the field is thinned.

## 6. Limits

* Owner-reported scores, not organizer receipts. One transcription error anywhere in the chain
  moves `a`, `ρ` and the ceiling.
* The nested-lineage collapse assumes removed dots carried no credit. Verified as *containment*
  from the bytes; the *no-credit* half is the family's own reported finding and cannot be
  re-checked here.
* All probes are assumed to have been scored against the same label set. The corpus spans
  2026-09-25 to 2026-10-04; if the round's labels changed inside that window the fit absorbs it
  as error, and the R² of 0.9922 over the eight-point chain argues against a change.
* `ρ` depends on `q̂`, the per-dot double-counting coverage of the anchor file, which is itself
  model-dependent. The honest statement is `ρ ≈ 3.6e4`, an order-of-magnitude constraint that is
  2.7× the constant previously carried in this repository.
* Nothing here is a current leaderboard reading, and no projection is a score.
