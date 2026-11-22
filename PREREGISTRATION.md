# Tilt — Research plan and pre-registration (v1.4)

Written on 15 November 2026, before any analysis of outcomes: so far only descriptive counts have been examined (`riassunto_dati.txt`, `statistiche_campione.txt`). To be committed to GitHub before phase 3: the commit date shows that the hypotheses precede the results.

*This is a faithful English translation of the original Italian plan (`PIANO_RICERCA_it.md`, v1), committed together with it. Section 11 records the amendments agreed after v1 was written and before any outcome analysis. Section 12 records the clarifications made at the end of phase 2, after testing the code on simulated data and before running any script on the real data. Section 13 records a second set of clarifications, made before `08_tilt.py` (the script that compares games after a loss and after a win) was ever run on the real data. Section 14 records the clarifications for question 2 (time pressure), made before `11_pressione.py` was ever run on the real data; at that date question 1 was closed and its results were known, which is stated openly. Italian original of sections 12 to 14: `PRECISAZIONI_it.md`.*

## 1. Hypotheses

| ID | Hypothesis and predicted direction | Role |
|---|---|---|
| H1a | Within the same session, against a different opponent, the score relative to expectation is lower right after a loss than right after a win (τ < 0) | Confirmatory, primary |
| H1b | The effect decreases with the break between the two games and with distance (game +1, +2, +3); after a break of more than 30 minutes it is about zero | Confirmatory |
| H1c | The effect is stronger at faster time controls (bullet > blitz > rapid) | Confirmatory |
| H1d | The effect is weaker as rating increases | Confirmatory |
| H1e | After a loss, players start the next game sooner, move faster in the first 10 moves and lose on time more often | Secondary (mechanism) |
| H2a | The probability of a blunder per move increases as remaining time decreases, with a sharp rise below 10 seconds | Confirmatory |
| H2b | Stronger players blunder less at every level of remaining time, and their relative increase below 10 seconds is also smaller | Confirmatory |
| H3 | Under tilt and time pressure, stronger players make proportionally more inaccuracies and fewer blunders | Deferred (specification only) |
| H4 | Momentum: after a win there is no gain beyond expectation | Exploratory, if time allows |

**Practical relevance threshold: 1 percentage point (pp) of score**, about 7 Elo points between equally rated players, roughly the rating change from a single game. With millions of games almost everything is "significant", so effect size decides:

- relevant tilt: estimate at −1 pp or beyond, and 95% confidence interval entirely below zero;
- negligible tilt: interval entirely between −1 and +1 pp;
- inconclusive: all other cases.

## 2. Operational definitions

| Term | Definition | Reason |
|---|---|---|
| Valid game | Result 1-0, 0-1 or ½-½, ratings and rating changes present, not Correspondence | An outcome and an expectation are needed |
| Time-control class | Current Lichess thresholds on estimated duration (initial time + 40 × increment): ultrabullet < 30 s, bullet < 180, blitz < 480, rapid < 1500, classical above | In 2017 "Rapid" did not exist: 600+0 was labelled Classical |
| Estimated end | `start_utc` + time consumed on both clocks (first clock − last clock + increments; for a player who loses on time, also the remaining time) | The end time is missing. It is a lower-bound estimate: it excludes network lag and the initial wait |
| Break | Start of the following game − estimated end of the previous one | Below −10 s the games overlap: the pair is excluded |
| Session | Games by the same player (all real-time controls, tournaments included) ordered by `start_utc, game_id`, with breaks of up to 30 minutes | Threshold fixed now; robustness at 10 and 60 minutes |
| Next game | The following game in the same session. Primary pair: both games outside tournaments, same class, different opponent | In a rematch, the player who just beat you is on average stronger than their rating: you would lose more even without tilt |
| Reference rating | The player's rating before their first game in that rating category (the 2017 categories) within the session; for pairs spanning two sessions, the rating at the start of the earlier session | It is not affected by the outcome under study. The current rating drops after a loss and would shift the expectation |
| Expected score E | Empirical table: mean score by class, colour and 25-point band of rating difference (reference − opponent), estimated on the first games of sessions | Lichess uses Glicko-2: the theoretical Elo formula is not calibrated on these data |
| Residual | Score (1, ½, 0) − E | Primary outcome: available for all games, not only the 8% with evaluations |
| Move loss | Drop in the mover's win probability between the evaluation before and after the move: Win% = 50 + 50 × (2 / (1 + e^(−0.00368 × cp)) − 1), with cp capped at ±1000 and mate = ±1000 | Lichess scale; gives little weight to errors in positions that are already decided |
| Error | Inaccuracy from 5 pp of loss, mistake from 10, blunder from 15 | Current Lichess thresholds (to be checked in the source code). The ?!, ?, ?? symbols in 2017 PGNs follow different rules: they are ignored |
| Remaining time | The mover's clock after their previous move | It is the time available when they start thinking |
| Stable rating | At least 50 valid games in the class in the month and median absolute rating change of at most 15 points | New ratings move by 25 points or more per game: the expectation is not reliable |
| Rating bands | < 1400, 1400–1599, 1600–1799, 1800–1999, ≥ 2000 (reference rating) | 10th, 50th and 90th percentiles at about 1283, 1646 and 2003 |

## 3. Data and sample

- May 2017: 11,693,919 games, 228,525 players. Games with evaluations are 8.2% (957,369), not 6%.
- **New streaming pass** over the `.pgn.zst` file (estimate: 15–30 minutes): for each game and colour, the first clock, the clock after the tenth move, the last clock and the number of moves. `partite.parquet` does not contain the clocks of games without evaluations, and they are needed for the estimated end, playing pace and photo-finish endings. The first clock also reveals berserk (time halved in tournaments).
- Sessions are built from all games; primary outcomes are non-tournament bullet, blitz or rapid games of players with a stable rating.
- Each game counts as an outcome for one player only, chosen with a hash of the `game_id`: the two rows of the same game have opposite residuals, and keeping both would bias the standard errors.
- **Exploration and confirmation**: 20% of players (hash of the username) is used to develop and debug the code; the remaining 80% is analysed only once, with frozen code.
- DuckDB with `memory_limit` at 5 GB and an on-disk temporary directory; always `ORDER BY start_utc, game_id`.

## 4. Method, question 1 (tilt)

τ = mean residual after a loss − mean residual after a win (draws treated separately).

1. **Estimator A, between sessions.** From each residual I subtract the mean of the same player's residuals in all *other* sessions: the player is compared with themselves. It still contains the "bad day" (low form that causes both the loss and the poor next game), so it is an upper bound of tilt.
2. **Estimator B, within session (primary).** τ is computed within each session and then averaged: this removes the bad day. In short sequences, however, this difference is biased by about +1/(n−1) even with independent games (Miller and Sanjurjo, 2018): 11 pp with 10 games, 1 pp with 100. Correction: I shuffle the order of games within each session 200 times, recompute τ and subtract the mean; the shuffled distribution also gives the p-value.
3. **Fatigue.** Before the comparison I subtract the mean residual by position in the session (1, 2, 3, 4–5, 6–10, 11–20, 21+) and class. The curve is also a result in itself.
4. **Decay (H1b).** τ_A by break band (up to 15 s, 15–60 s, 1–5 min, 5–30 min, over 30 min, over 6 h) and by distance +1, +2, +3. The over-30-minutes band is the negative control: an equal effect there too would point to form or rating, not tilt. The break is chosen by the player: this curve is descriptive.
5. **Causal check 1, photo-finish endings.** Games without increment lost on time with the winner at 3 seconds or less: the outcome is almost a coin toss. I compare the next game of the loser and of the winner of the same game (same duration, time of day and fatigue), after checking that the two groups were similar beforehand.
6. **Causal check 2, colour as an instrument.** Colour is assigned almost at random and White wins more often (49.6% vs 46.5%): having had Black in the previous game makes it more likely to have lost it, independently of form. τ_IV = difference in residual between players who had Black and players who had White, divided by the difference in the share of losses, holding the current colour fixed; only players with a White share between 45% and 55%. With a single month the expected precision is about ±3 pp: it can only rule out large effects, and becomes useful when more months are added.
7. **Selection.** (a) Probability of ending the session after a loss and after a win. (b) τ in arena tournaments, where the next pairing is automatic and the choice to continue matters less. (c) Games after a loss reweighted by the inverse of the estimated probability of continuing. In any case τ measures the effect on the games actually played after a loss, i.e. the answer to "should I keep playing?"; it does not say how the players who stopped would have played.
8. **Inference.** Cluster bootstrap over players (1000 resamples of per-player sums), 95% intervals. Estimates weighted by game and, in parallel, by player, to rule out that a few very active players drive the result.
9. **Moderators.** τ by class (H1c) and linear interaction with rating per 200 points (H1d).

Secondary outcomes (H1e), with the same estimators: break before the next game, seconds per move in moves 2–10 relative to the player's habit in that time control, loss on time.

## 5. Method, question 2 (time pressure)

- Unit: the move, in games with evaluations and without increment. Outcome: blunder; in parallel, mean loss.
- Exposure: remaining time in bands (< 3, 3–5, 5–10, 10–20, 20–40, 40–80, 80–160, > 160 s).
- Comparison within the same game and the same player (subtracting the game-player mean), holding fixed the phase (move number in bands, captures already made as a measure of material) and the balance (Win% before the move in bands): a player who is already lost can no longer make big errors.
- Separate curves by class and rating band; confirmatory tests on blitz (in 60+0 bullet, "more than 60 seconds" does not exist).
- Robustness: comparison between the two players within the same 10-ply window (same complexity, different clocks).
- Known limitation: a difficult position consumes time and stays difficult; phase and balance control for this only partly.

## 6. Question 3 and momentum (specification only)

- H3: shares of inaccuracies, mistakes and blunders by rating band, in three conditions: normal, after a loss, below 10 seconds.
- H4: estimators A and B with the state "current streak" (1, 2, 3+ consecutive wins or losses in the session).

## 7. Is the evaluated sample biased?

Three checks before using it:

1. Standardized differences between games with and without evaluations (rating, length, class, termination, result, tournament).
2. By player: does the probability that a game was analysed depend on the outcome of the previous game or on its own result? This is the check that matters for tilt.
3. Share of games from "systematic analysers" (at least 30 games, at least 80% of them analysed).

Rule: if in check 2 the probabilities differ by more than 10% in relative terms, errors after a loss are measured only on (i) systematic analysers and (ii) plan B: about 6,000 games drawn at random in pairs (after a loss and after a win, same player), analysed locally with Stockfish at fixed nodes (100,000 per position, estimated 3–4 hours on 4 threads). Question 2 compares moves within the same game: there, selection only limits generalisability.

## 8. Multiple testing and robustness

- Six confirmatory tests (H1a, H1b, H1c, H1d, H2a, H2b) with Holm correction at 5%. Everything else is exploratory, reported with intervals and Benjamini-Hochberg (FDR) correction.
- Robustness checks already decided: session threshold at 10 and 60 minutes; rematches included; current rating instead of reference rating; both sides of each game; games under 10 plies and Abandoned games excluded; looser and stricter stable-rating thresholds; photo finish at 5 seconds.
- Exploratory: type of loss (on time or on the board, expected or surprising, a thrown-away win in the evaluated sample).

## 9. Risks

| Risk | Countermeasure |
|---|---|
| Wrong estimated end | Negative breaks expected below 1%; the histogram of the log break should have two humps with the valley near 30 minutes |
| The `.pgn.zst` file is no longer on disk | Re-download it (a few GB) before phase 2 |
| 8 GB of RAM | Only SQL aggregates and numpy on per-player sums; no heavy regression library |
| May 2017 does not represent today | Code parametrised by month; replication on a recent month after the deadline |
| Unstable ratings, duplicate accounts, cheaters | Stability filter; the rest is noise unrelated to the previous outcome |
| Time and quota | Cut order: H4, H3, causal check 2, question 2 |

## 10. Timeline (deadline: Tuesday 17 November 2026, 08:59 UTC+1)

- Sunday: plan approval, commit, phase 2 code, new pass over the file, sessions on the 20% exploration set.
- Monday morning: question 1 on the 80% confirmation set, with robustness checks.
- Monday afternoon and evening: critical review, interview kit, question 2 if quota remains.

## 11. Amendments agreed before any outcome analysis (v1.1)

1. Causal check 2 (colour as an instrument) is moved out of this sprint and kept as future work, for when more months are added: with a single month its expected precision (±3 pp) is coarser than the 1 pp relevance threshold. It was not one of the confirmatory tests.
2. Question 2 (H2a, H2b) is carried out only after question 1 is complete. If it does not fit in this sprint it will be run later, with the hypotheses and method stated here unchanged.
3. The number of permutations (200) and bootstrap resamples (1000) may be reduced if computation time on the available hardware requires it; the estimators do not change.
4. Minimum deliverable: H1a with estimators A and B, the negative control (breaks over 30 minutes) and causal check 1 (photo-finish endings).

## 12. Clarifications after testing on simulated data (v1.2)

Written on Sunday 15 November 2026, at the end of phase 2, **before running any script on the real data**. All of them come from tests on simulated data (`tests/simula_dati.py`), where the true effect is known. They must be committed before `08_tilt.py` is run on the real data: the commit date shows that they precede the results.

### P1. Estimator B: unexpected result instead of loss/win

- **Plan**: within the session, mean residual after a loss − mean residual after a win.
- **Now**: regression, with block fixed effects, of the residual y(t) on the residual y(t−1), i.e. on the *unexpected* result of the previous game (score − expected). I report τ = −slope: between a loss and a win the residual changes by one point, so τ still reads as "after a loss − after a win".
- **Why**: the within-session loss/win comparison is biased by the pairing system. If I win, my rating goes up, I face stronger opponents and lose more often *afterwards*: wins and losses are not exchangeable even without tilt, and shuffling does not correct this. The residual already accounts for the opponent's strength.
- **Evidence**: on simulated data without tilt, the plan's version gives −1.06 pp (95% CI −1.74 to −0.43), the new one −0.01 pp (−0.66 to 0.68). Two other seeds, two-sided: +0.07 and −0.05 pp (standard error 0.21).
- The plan's version remains in the output, labelled as biased, for transparency.

### P2. Bias correction: division by (1 − b)

- **Plan**: corrected τ = observed τ − mean of the shuffles (b).
- **Now**: τ_B = (observed τ − b) / (1 − b).
- **Why**: the short-sequence bias also shrinks a true effect towards zero, by the factor (1 − b). With b between 0.11 and 0.16, subtraction alone underestimates the effect by 11–16%.
- **Evidence**: simulated Markov chain with a true τ of −2.00 and −5.00 pp: subtraction gives −1.67 and −4.15; with the division −2.00 and −4.94. With the full chain of scripts and a 30-Elo tilt (about −4.0 pp): τ_B = −3.86 pp (95% CI −4.55 to −3.17).

### P3. Shuffles: within the block, last game fixed

- **Plan**: shuffle the order of games within each session.
- **Now**: shuffle within each *block*, keeping the last game of the block in last position.
- **Why**: the decision to stop depends on the last outcome, so the last game is not exchangeable with the others; the first n−1 are, if order does not matter. The scheme with all games shuffled is reported alongside: if the two estimates differ, the stopping rule matters.

### P4. Unit of estimator B: the block

- Block = uninterrupted sequence, within a session, of valid, non-tournament games of the same class that do not overlap (break not below −10 s). A tournament game, a change of class or an invalid game ends the block.
- Weights: those of the fixed-effects regression (sum of squared deviations of x within the block). "Averaged" in the plan was ambiguous; in parallel I report the estimate with equal weight per player.

### P5. Sampling details

- Exploration/confirmation group: MD5 of the lower-case username, modulo 100; below 20 = exploration.
- Side chosen for each game: parity of the last character of the `game_id` (instead of a hash: same purpose, reproducible everywhere).
- Rematch: an attribute of the game (same opponent as the previous game in the true order); a rematch does not serve as an outcome but does serve as "previous game".

### P6. Expected score and auxiliary quantities

- Empirical curve by class and colour: means in 25-point bands on the first games of sessions of stable players, linear interpolation between bands (at least 200 games per band); in the tails, a logistic curve estimated on the same bands and joined without jumps; rating differences capped at ±600.
- The curve, the position correction and the player baselines are computed on all players (they do not contain the after-loss/after-win comparison). The scripts print no outcome of the confirmation group before `08_tilt.py --gruppo conferma --codice-bloccato`.
- Baseline for pairs spanning two sessions (negative control): it excludes *both* sessions, because the earlier one contains the game that defines the condition (otherwise there is about +1 pp of mechanical bias with 100 games).

### P7. Operational definition of the confirmatory tests

| Hypothesis | Statistic | Test |
|---|---|---|
| H1a | τ_B, all classes, game +1 | Permutation; decision with the 1 pp rule on the 95% CI |
| H1b | τ_B(+1) − τ_B(+2), i.e. effect of the previous game minus effect of the game two before | Bootstrap over players, normal p |
| H1c | τ_B bullet − τ_B rapid | Bootstrap over players, normal p |
| H1d | Slope of τ_B per +200 points of reference rating | Permutation |

- The curve of τ_A by break and the negative control remain **descriptive**: on simulated data without tilt, A's "short break − negative control" difference is already −1.1 pp, because daily form weighs more within a session than between sessions.
- Known limitation, measured in simulation: τ_B at distance +2 and +3 is pushed towards zero by about b × τ(+1) (0.3–0.4 pp with τ(+1) = −4 pp). H1b is therefore slightly favoured; this must be stated among the limitations.

### P8. Photo finish

- Primary estimate as in the plan (winner at 3 seconds or less), with each player compared with their own baseline. Robustness: 5 seconds; loser at 10 seconds or less.
- New reading criterion: the balance table decides whether the photo finish is really close to random (standardized differences below 0.1 on rating advantage, expected score in the game, baseline, previous score). If it is not, the estimate is to be read as a variant of estimator A, not as a causal check.

### P9. Other

- Error thresholds verified in the Lichess source code (`Advice.scala`): 0.1 / 0.2 / 0.3 on the −1 to +1 scale, i.e. 5 / 10 / 15 pp of Win%. They match the plan.
- DuckDB memory limit: 4 GB by default (not 5), to leave headroom for Windows on 8 GB of RAM.
- Number of shuffles (200) and bootstrap resamples (1000) confirmed: run times measured (see `HANDOFF.md`).

## 13. Second set of clarifications, before running `08_tilt.py` (v1.3)

Written on Monday 16 November 2026. At this date, `05`, `06`, `09` and `07` had been run on the real data (structural diagnostics; for the exploration group only, the mean residual by position in the session and the checks on the evaluated sample). **`08_tilt.py` had never been run on the real data**: no after-loss/after-win comparison had been seen. P10 and P11 come from tests on simulated data; P12 comes from reading the output of `09` on the exploration group, and this is stated openly. They must be committed before running `08`.

In the tables: means over several independent simulations (different seeds) ± standard error of the mean, in pp; confirmation group of the simulated data, 4,000 players per simulation. A 30-Elo tilt is worth about −3.9 pp; 15 Elo about −1.95 pp.

### P10. Decay curve and H1b test: joint estimate

- **P7**: H1b = τ_B(+1) − τ_B(+2), with a separate regression for each distance, each corrected with shuffles. Stated limitation: at +2 and +3 the estimate is "pushed towards zero by 0.3–0.4 pp".
- **Problem**: that limitation was wrong in sign and in size. With a true tilt only at +1 (about −3.9 pp), the separate regression at +2 gives **+0.88 ± 0.13** (7 seeds; seed 1: +1.09, 95% CI 0.42 to 1.78), at +3 +0.71 ± 0.19, and H1b −4.58 instead of −3.9. Without tilt the bias is absent (−0.24 ± 0.19). On the real data a tilt at +1 would have appeared as a false "rebound" two games later, and H1b, a confirmatory test, would have been inflated.
- **Why**: once the block mean is removed, the products between all pairs of games in a block have a fixed sum. If pairs at distance 1 are more alike than average (tilt at +1), the other pairs must be less alike than average. Shuffles do not correct this: their benchmark is all pairs in the block, including those at distance 1.
- **Now**: the three distances are estimated jointly, and the benchmark contains none of them. For each game t serving as an outcome, only its past within the block is used:
  - x_d = unexpected result of the game d places earlier (d = 1, 2, 3);
  - z_d = x_d − mean result of the *distant* games (at least 4 places before t) in the same block and of the same selection type as the game d places earlier (types are defined in P11);
  - the coefficients b_1, b_2, b_3 jointly solve Σ_t y_t z_d = Σ_k b_k Σ_t x_k z_d (d = 1, 2, 3); τ(+d) = −b_d.

  This is the regression of y_t on the three previous results, in which the deviation from the distant games acts as an instrument: b_d is the effect of the result d games earlier, holding the other two fixed. No shuffles and no (1 − b) correction are needed, because z uses only games before t (no mean containing y_t) and imposes no condition on what happens after t.
- **H1b test** (replaces the corresponding row of P7): τ(+1) − τ(+2) from the joint estimate; bootstrap over players, normal p, as in P7.
- **Assumption and cost**: after 3 games the effect is over; only outcomes with at least 4 previous games in the block count (blocks of 5 games or more). In simulation the standard error at +1 is 0.42, against 0.32 for estimator B; with many rematches, 0.65 against 0.45.
- The separate regressions remain in the output, labelled as biased.

| Simulated scenario | Seeds | Joint +1 | +2 | +3 | H1b | Separate +2 (P7) |
|---|---|---|---|---|---|---|
| No tilt | 7 | −0.06 ± 0.22 | 0.07 ± 0.16 | 0.18 ± 0.15 | −0.13 ± 0.22 | −0.24 ± 0.19 |
| Tilt 30 (−3.9 at +1) | 7 | −3.73 ± 0.15 | 0.18 ± 0.19 | 0.29 ± 0.15 | −3.92 ± 0.24 | **+0.88 ± 0.13** |
| Tilt 30 and tilt2 15 (−3.9 and −1.95) | 7 | −4.01 ± 0.28 | −1.73 ± 0.11 | 0.02 ± 0.18 | −2.28 ± 0.32 | −1.10 ± 0.09 |
| No tilt, "realistic" rematches (see P11) | 4 | −0.20 ± 0.19 | 0.05 ± 0.34 | −0.12 ± 0.09 | −0.25 ± 0.20 | −0.13 ± 0.24 |
| Tilt 30, "realistic" rematches | 4 | −3.87 ± 0.26 | 0.10 ± 0.25 | −0.42 ± 0.25 | −3.98 ± 0.40 | **+1.08 ± 0.28** |

Seed 1, as in the check that found the problem: `--tilt 30` → +1 −3.89 (95% CI −4.66 to −3.13), +2 **+0.60 (−0.29 to 1.41)**, +3 −0.15, H1b −4.49; `--tilt 30 --tilt2 15` → +1 −4.87 (−5.69 to −4.00), +2 −1.69 (−2.55 to −0.80), +3 −0.28, H1b −3.17. Over 11 scenarios and 55 simulations, the spread of the estimates across seeds is in line with the bootstrap standard error (ratios between 0.88 and 1.18).

### P11. Shuffles: fixed structure, swaps within the selection type (replaces P3)

- **P3**: shuffle the order of games within the block, last game fixed. In the code, each game moved together with its attributes (whether it is a rematch, whether it is the chosen side).
- **Problem**: rematches do not serve as outcomes and come in streaks. Which games enter the regression is a *structure* of the block, and the short-sequence bias depends on that structure (on how many games serve both as previous game and as outcome). Moving games together with their attributes scatters the rematches, so the structure of the shuffles is no longer the true one and b is underestimated. Evidence, **without any tilt**, with streaks of rematches (probability 0.75 of another rematch after a rematch), code of the previous commit: τ_B = +1.47, +1.26, +1.42, +0.89 over four seeds (mean **+1.26**; all four 95% CIs exclude zero, permutation p 0.005). If, in addition, a rematch is more likely after a loss (0.40 against 0.12): mean **+2.0**. In the real data, rematches make up between 26% (rapid) and 50% (bullet) of the pairs within blocks (`06_diagnostiche.txt`): the primary estimator would have had a positive bias, capable of hiding a tilt or of simulating a rebound.
- **Now**:
  1. the structure stays fixed: which games are rematches, which serve as outcomes, which is the last. Only the results (y and score) are swapped;
  2. a result can only move to the place of a game of the same **selection type**: what follows the game (a different opponent, a rematch, the end of the block) × whether the game itself is a rematch. Stopping and asking for a rematch depend on the result just obtained: this is the same reason as the "last game fixed" of P3, extended to rematches. With `--rivincite`, only "last" counts.
  - The `rim_libero` column swaps results among all games of the block, with the structure fixed: if it differs, the selection rules matter. The script also prints the probability of a rematch after a loss and after a win.
- The observed statistic does not change; b and the permutation p-values of H1a and H1d do.
- **Rule for H1a**: it stays on τ_B. If the joint estimate at +1 (P10) leads to a different verdict under the 1 pp rule, I report both and the verdict is "inconclusive".

| Simulated scenario | Seeds | τ_B, previous commit | τ_B, now | `rim_libero` |
|---|---|---|---|---|
| No tilt | 7 | — | 0.14 ± 0.17 | 0.11 ± 0.15 |
| No tilt, streaks of rematches (0.75) | 4 | **+1.26** | 0.04 ± 0.13 | 0.01 ± 0.08 |
| No tilt, streaks and rematch after a loss (0.40) | 4 | **+2.01** | −0.34 ± 0.27 | −0.11 ± 0.26 |
| No tilt, rematch after a loss (0.60), no streaks | 9 | — | 0.04 ± 0.14 | 0.00 ± 0.16 |
| No tilt, "realistic": streaks, rematch after a loss 0.40, opponent keeps their true strength | 4 | — | 0.10 ± 0.16 | 0.24 ± 0.14 |
| Tilt 30 (−3.9) | 7 | — | −3.71 ± 0.09 | −3.76 ± 0.09 |
| Tilt 30, "realistic" | 4 | — | −3.39 ± 0.13 | −3.57 ± 0.18 |
| Tilt 30 and tilt2 15 | 7 | — | −3.35 ± 0.15 | −3.43 ± 0.14 |

- **Measured limitations** (all conservative, i.e. towards zero): τ_B is shrunk by 5% in the base simulator and by 13% in the realistic scenario (the (1 − b) correction is approximate, and swapping within type conditions on what follows the outcome game); by 14% if the effect lasts two games, because B assumes it lasts one. The joint estimate at +1 does not have these limitations (−3.87 and −4.01 in the same scenarios) but is less precise.
- Unmeasured limitation: if stopping or asking for a rematch depends on more than the last result (for example on two losses in a row), the types are not enough.
- New options in `tests/simula_dati.py` for these checks: `--rivincita-sconfitta`, `--rivincita-catena`, `--avversario-stabile`, `--verita`.

### P12. Evaluated sample: the verdict of check 2 is read within the player

Written after reading `09_controlli_eval_esplorazione.txt`; it does not concern any confirmatory test.

- **Plan (section 7)**: "by player: does the probability that a game was analysed depend on the outcome of the previous game or on its own result?", with a threshold of 10% relative.
- **Problem**: the script printed the verdict on the shares of all players pooled (table 2a). For "the game's own result" that comparison cannot say anything: every decided game has a winner and a loser, so the two shares are equal by construction (8.36% and 8.38%).
- **Now**: the verdict uses the within-player comparison (table 2b). On the exploration group: outcome of the previous game 13.19% against 14.24%, i.e. −7.4% (within the threshold); the game's own result 12.59% against 16.24%, i.e. **−22.5% (beyond the threshold)**: among players whose games are only sometimes analysed, won games are analysed more often than lost ones.
- **Consequence**, following the plan's rule: errors "after a loss" are not measured on Lichess evaluations, except for systematic analysers (89 players, 2.2% of analysed games) and with plan B (local Stockfish). This concerns H3 and the exploratory analysis of the type of loss, both outside this sprint. Question 1 uses the score of all games and is unaffected. Question 2 compares moves within the same game: it remains valid, but it applies to a sample in which 2017 "Classical" makes up 35.6% (against 23.0% among non-analysed games) and draws are analysed less often (5.3% against 8.4% of decided games): its curves must be read by class.

## 14. Third set of clarifications (P13): question 2, time pressure (v1.4)

Written on Tuesday 17 November 2026, at night. At this date **`11_pressione.py` had never been run on the real data**, on either group: of the move-level data, only the overall summary printed by `07_mosse.py` and the checks of `09` had been seen. No comparison between moves played with little and with plenty of time had been seen. Question 1, on the other hand, is closed: its four p-values are known, and this is stated because Holm needs them (P13.4). Everything below comes from tests on simulated moves (`tests/simula_mosse.py`), where the true effect is known. To be committed together with `11_pressione.py` **before** running it.

### P13.1 Sample and variables (choices the plan did not fix)

- **Moves**: `data/mosse.parquet` joined to `data/analisi` by game and colour. A move enters if it has a loss, a Win% before the move and a remaining time (the first ply of the game has no "before"), and if the game is valid, has engine evaluations, has **no increment**, and is bullet, blitz or rapid (current thresholds).
- **Group**: that of the player who moves. The two players of a game can be in different groups: each contributes only their own moves.
- **Tournaments included** (the plan does not exclude them; with berserk, what counts is the mover's own clock anyway). **Stable rating not required**: here the rating only places the player in a band. Robustness variants: `--senza-tornei` (no tournaments), `--stabile` (stable rating only).
- **Blunder** = judgement 3 in `07_mosse.py` (loss of at least 15 points of Win%). **Mean loss**: negative losses (engine noise) count as zero.
- **Remaining time** = `clk_prima`, in whole seconds. Bands closed on the left: 0–2, 3–4, 5–9, 10–19, 20–39, 40–79, 80–159, 160 and above. Reference band for the curves: 20–40 s, the only central band that exists in all classes.
- **Strata** ("holding phase and balance fixed"), crossed with each other, 6 × 7 × 7 = 294:
  - the player's move number: 1–10, 11–20, 21–30, 31–40, 41–50, 51 and above;
  - captures already made in the game: 0–3, 4–7, 8–11, 12–15, 16–19, 20–23, 24 and above;
  - Win% before the move: below 15 (a blunder is impossible), 15–30, 30–45, 45–55, 55–70, 70–85, 85 and above.
- **Level**: reference rating of the row, in the plan's five bands.
- **Pair** = game × player: this is the unit whose level is removed.

### P13.2 Multiplicative model instead of the additive one (deviation from the plan)

- **Plan**: "comparison within the same game and the same player (subtracting the game-player mean)", i.e. an additive model: blunder = a[pair] + β[time band] + γ[stratum].
- **Problem**: if pairs have different error levels and the level *multiplies* the risk (someone who blunders twice as often does so in every phase), then in the pairs that blunder more the risk rises more, in absolute terms, as the game goes on. The additive model cannot represent this and attributes it to time, which in every game decreases as moves go by. Evidence, **without any time effect**: +0.68 ± 0.06 pp (6 seeds, raw difference 3 pp) in the base scenario; with 240,000 games, +0.34 ± 0.04 without resignations, and 0.00 ± 0.04 if all pairs at the same level have the same risk. With a different structure the sign flips (−0.46 pp in `tests/verifica_11.py`): the direction of the error is not predictable.
- **Now** (primary): a multiplicative model, i.e. a fixed-effects Poisson regression:
  probability of a blunder = a[pair] × B[time band] × C[stratum].
  B[k] / B[j] is the **risk ratio** (RR) between two time bands, within the same game, for the same player and in the same stratum. The pair's level is removed by dividing, not subtracting. It does not require blunders to follow a Poisson distribution: only the mean must have this form. Pairs without blunders and strata where a blunder is impossible carry no information and get zero weight on their own.
- **Effect in percentage points**, reported next to the RR: among the moves played with less than 10 seconds, observed rate × (1 − 1/RR), i.e. how many more blunders per 100 moves compared with the same moves without the risk ratio.
- The additive model remains in the output, in pp, labelled "plan's model": it does not enter the verdicts.
- **Estimation**: iterative proportional fitting (30 rounds), then Newton steps. Strata are estimated on the analysed group, together with the rest: no auxiliary quantity comes from the other group.
- **Inference**: cluster bootstrap over players, 1000 resamples, seed 20170501. Each player's contributions to the estimate are resampled (the sum, over their moves, of "observed − predicted", passed through the inverse of the full model's information matrix): the uncertainty on the strata is included, and the matrix is that of the whole sample. All cells of a class use the same resamples. Intervals: 2.5 and 97.5 percentiles. p-values: two-sided normal, estimate / bootstrap standard error (as for H1b and H1c in P7).
- **Identity checks** (`tests/verifica_11.py`, passed): same coefficients as a brute-force regression with one dummy per pair (difference 1e-13 for the additive model, 1e-16 for the multiplicative one); same robust standard error; on truly multiplicative data the inserted RR is recovered (true log RR 0 → −0.004 ± 0.003; true 0.693 → 0.701 ± 0.003), and the spread of the estimates over 150 replications is 0.94–1.10 times the computed standard error.

### P13.3 Statistics of the two confirmatory tests (on blitz, as in the plan)

| Hypothesis | Statistic | Test | Prediction |
|---|---|---|---|
| H2a | log RR of "less than 10 seconds" vs "10 seconds or more", blitz, all levels | Bootstrap over players, two-sided normal p | > 0 |
| H2b | Slope of the log RR across the five level bands: Σ c_f · log RR_f with c = (−2, −1, 0, 1, 2) / 10. It is the least-squares line through five equally spaced points and reads "per level band" (about 200 rating points). A separate model per band, same resamples | Bootstrap over players, two-sided normal p | < 0 |

- Each hypothesis has two parts; the confirmatory test covers one of them, the other is descriptive:
  - H2a, "with a sharp rise below 10 seconds": 8-band curve and sharp-rise index = [log RR(5–10) − log RR(10–20)] − [log RR(10–20) − log RR(20–40)]. The three bands double in width: the index is positive if the risk accelerates below 10 seconds.
  - H2b, "stronger players blunder less at every level of remaining time": for each level band and time band, observed / expected blunders (expected = the class's mean rate in the same stratum and the same time band); difference between ≥ 2000 and < 1400 with 95% CI.
- In parallel, descriptive: mean loss of Win% (multiplicative ratio and additive difference).
- A cell enters only with at least 200 blunders below 10 seconds. If a level band does not reach this in blitz, H2b cannot be computed and counts as not rejected.
- Bullet and rapid, the curves by level and all other estimates: descriptive, reported with intervals (and FDR correction if p-values are reported).

### P13.4 Holm: the thresholds that apply to H2a and H2b

- The family remains six tests at 5%. The four p-values of question 1 are known: H1c 0.0009; H1a 0.42; H1d 0.49; H1b 0.94.
- Holm sorts the six p-values and compares them with 0.05/6, 0.05/5, 0.05/4… stopping at the first non-rejection. Since 0.0009 passes any threshold and the other three are above 0.05, the rule for question 2 becomes:
  - the **smaller** of p(H2a) and p(H2b) is rejected if it is **≤ 0.0100** (0.05/5);
  - the **larger** is rejected only if the first one is, and if it is **≤ 0.0125** (0.05/4).
- The verdicts of question 1 cannot change: H1c stays rejected whatever happens, and the other three stay not rejected. The script prints the full table.
- As with H1c: an equality rejected **in the direction opposite** to the prediction refutes the hypothesis.

### P13.5 Reading rules (fixed before running)

The plan did not fix a relevance threshold for question 2. I fix it now, above the method error measured in simulation (P13.6).

- **H2a** (RR in blitz, all levels):
  - **confirmed**: equality rejected with Holm and 95% CI of the RR entirely above **1.10**;
  - **refuted**: equality rejected and 95% CI entirely below 0.90;
  - **negligible**: 95% CI entirely between 0.91 and 1.10;
  - **inconclusive**: all other cases.
  - "Sharp rise" is written only if the 95% CI of the sharp-rise index is entirely above zero; otherwise "rises as time runs out", without "sharp rise".
- **H2b** (slope in blitz):
  - second part **confirmed**: equality rejected and negative slope;
  - second part **refuted**: equality rejected and 95% CI entirely above **+0.04** (in simulation the slope has a positive error of up to +0.035);
  - **not confirmed**: all other cases.
  - first part: "at every level of remaining time" holds if, in all time bands with data, the 95% CI of (≥ 2000) − (< 1400) on the observed/expected ratio is entirely below zero.
  - H2b is confirmed as a whole only if both parts hold; otherwise, say which one.
- The verdicts apply to the confirmation group. The exploration group is used to test the code; after exploration, the code may be changed only for execution or identity errors, declared in a P14 before the confirmation run.
- **Wording**: "more blunders are made", not "people play worse"; the RR always with its equivalent in pp and with the base rate; never "cause": a difficult position consumes time and stays difficult (limitation stated in the plan). The result applies to games analysed by the engine, without increment, and is read by class (P12).

### P13.6 Test on simulated moves

`tests/collaudo_11.py`: 120,000 games and 10,000 players per simulation, confirmation group of the simulated data, blitz; mean ± standard error across seeds. The simulator has different error levels per pair (linked to playing pace), resignation by the losing side, checkmate, and flagging. "True" for H2a = ratio between the relative risk inserted below 10 seconds and the one inserted above.

| Simulated scenario | Seeds | True H2a | Estimated H2a | True H2b | Estimated H2b | Additive (pp) | Windows (log RR) |
|---|---|---|---|---|---|---|---|
| No time effect | 6 | 0 | **0.031 ± 0.006** | 0 | 0.002 ± 0.006 | **0.68 ± 0.06** | **0.118 ± 0.006** |
| No effect, hidden position difficulty | 2 | 0 | **−0.057 ± 0.006** | 0 | 0.028 ± 0.012 | 0.29 ± 0.09 | 0.094 ± 0.013 |
| No effect, no resignation when short of time | 2 | 0 | −0.007 ± 0.010 | 0 | 0.019 ± 0.004 | 0.44 ± 0.03 | 0.094 ± 0.021 |
| Multiplicative effect, smaller for stronger players | 6 | 0.732 | 0.631 ± 0.004 | −0.050 | −0.015 ± 0.006 | 10.27 | 0.607 |
| Multiplicative effect, equal for all | 4 | 0.727 | 0.635 ± 0.006 | 0.017 | 0.035 ± 0.005 | 10.34 | 0.621 |
| Multiplicative effect, hidden difficulty | 2 | 0.684 | 0.519 ± 0.006 | −0.019 | −0.008 ± 0.005 | 10.56 | 0.554 |
| Additive effect (same pp for all) | 2 | 0.330 | 0.315 ± 0.001 | 0.095 | 0.097 ± 0.000 | 4.29 | 0.365 |

- **Without effect** the primary log RR lies between −0.06 and +0.03, i.e. an RR between 0.94 and 1.03: hence the 1.10 threshold.
- **With a true effect** the estimate is shrunk towards zero by 5% to 24%: conservative. The 8-band curve is instead slightly steeper than the truth at both ends (in a 240,000-game simulation, below 3 s: 3.07 estimated vs 2.73; above 160 s: 0.78 vs 0.91): the RRs of the extreme bands are to be read as orders of magnitude.
- **H2b**: error between 0.00 and +0.035, always in the direction opposite to the hypothesis. If the true slope is negative the estimate is attenuated (−0.015 vs −0.050): a "not confirmed" may be a false negative, and this must be stated.
- **Sharp-rise index**: without effect −0.002 ± 0.015; with the inserted effect 0.187 ± 0.010 (true 0.18).
- **Standard errors**: spread across seeds / bootstrap standard error between 0.85 and 1.02 for H2a, and between 0.79 and 1.29 for H2b (4–6 seeds).
- **Window robustness check** from the plan (the two players within the same 10-ply window; strata: balance × rating gap): without effect it gives +0.09 / +0.12 when players who think longer blunder more. It does not remove differences between the two players: it is read only for its sign and does not enter the verdicts.
- **Unresolved limitations**: hidden difficulty moves the estimate in both directions (−0.06 without effect; −24% with effect); the simulator is not Lichess; strata are banded, and residual confounding remains within a band.

### P13.7 What to report

1. Sample: pairs, games and moves per class; share of moves below 10 seconds; pairs with moves both above and below 10 seconds.
2. H2a: RR with 95% CI, p, verdict; raw rate below and above 10 seconds; equivalent in pp; sharp-rise index with 95% CI.
3. H2b: slope with 95% CI, p, verdict; the five RRs by level band; observed/expected table.
4. Holm table over the six tests.
5. 8-band curves by class and by level (chart: RR on a log scale against remaining time, one line per level band, one panel per class).
6. Alongside, always: additive estimate (plan's model), window robustness check, `--senza-tornei` and `--stabile` variants, mean loss. If any of these has the opposite sign to the primary estimate, it must be stated in the same sentence as the result.
7. Deviations from the pre-registration: multiplicative model instead of the additive one; relevance threshold fixed after the plan; Holm computed with the p-values of question 1 already known.
