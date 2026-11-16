# Tilt — Research plan and pre-registration (v1.3)

Written on 15 November 2026, before any analysis of outcomes: so far only descriptive counts have been examined (`riassunto_dati.txt`, `statistiche_campione.txt`). Committed to GitHub before phase 3: the commit date shows that the hypotheses precede the results.

_This is a faithful English translation of the original Italian plan (`PIANO_RICERCA_it.md`, v1), committed together with it. Section 11 records the amendments agreed after v1 was written and before any outcome analysis. Section 12 records the clarifications made at the end of phase 2, after testing the code on simulated data and before running any script on the real data. Section 13 records a second set of clarifications, made before `08_tilt.py` (the script that compares games after a loss and after a win) was ever run on the real data. Italian original of sections 12 and 13: `PRECISAZIONI_it.md`._

## 1. Hypotheses

| ID  | Hypothesis and predicted direction                                                                                                                    | Role                          |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| H1a | Within the same session, against a different opponent, the score relative to expectation is lower right after a loss than right after a win (τ < 0)   | Confirmatory, primary         |
| H1b | The effect decreases with the break between the two games and with distance (game +1, +2, +3); after a break of more than 30 minutes it is about zero | Confirmatory                  |
| H1c | The effect is stronger at faster time controls (bullet > blitz > rapid)                                                                               | Confirmatory                  |
| H1d | The effect is weaker as rating increases                                                                                                              | Confirmatory                  |
| H1e | After a loss, players start the next game sooner, move faster in the first 10 moves and lose on time more often                                       | Secondary (mechanism)         |
| H2a | The probability of a blunder per move increases as remaining time decreases, with a sharp rise below 10 seconds                                       | Confirmatory                  |
| H2b | Stronger players blunder less at every level of remaining time, and their relative increase below 10 seconds is also smaller                          | Confirmatory                  |
| H3  | Under tilt and time pressure, stronger players make proportionally more inaccuracies and fewer blunders                                               | Deferred (specification only) |
| H4  | Momentum: after a win there is no gain beyond expectation                                                                                             | Exploratory, if time allows   |

**Practical relevance threshold: 1 percentage point (pp) of score**, about 7 Elo points between equally rated players, roughly the rating change from a single game. With millions of games almost everything is "significant", so effect size decides:

- relevant tilt: estimate at −1 pp or beyond, and 95% confidence interval entirely below zero;
- negligible tilt: interval entirely between −1 and +1 pp;
- inconclusive: all other cases.

## 2. Operational definitions

| Term               | Definition                                                                                                                                                                                    | Reason                                                                                                                                     |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Valid game         | Result 1-0, 0-1 or ½-½, ratings and rating changes present, not Correspondence                                                                                                                | An outcome and an expectation are needed                                                                                                   |
| Time-control class | Current Lichess thresholds on estimated duration (initial time + 40 × increment): ultrabullet < 30 s, bullet < 180, blitz < 480, rapid < 1500, classical above                                | In 2017 "Rapid" did not exist: 600+0 was labelled Classical                                                                                |
| Estimated end      | `start_utc` + time consumed on both clocks (first clock − last clock + increments; for a player who loses on time, also the remaining time)                                                   | The end time is missing. It is a lower-bound estimate: it excludes network lag and the initial wait                                        |
| Break              | Start of the following game − estimated end of the previous one                                                                                                                               | Below −10 s the games overlap: the pair is excluded                                                                                        |
| Session            | Games by the same player (all real-time controls, tournaments included) ordered by `start_utc, game_id`, with breaks of up to 30 minutes                                                      | Threshold fixed now; robustness at 10 and 60 minutes                                                                                       |
| Next game          | The following game in the same session. Primary pair: both games outside tournaments, same class, different opponent                                                                          | In a rematch, the player who just beat you is on average stronger than their rating: you would lose more even without tilt                 |
| Reference rating   | The player's rating before their first game in that rating category (the 2017 categories) within the session; for pairs spanning two sessions, the rating at the start of the earlier session | It is not affected by the outcome under study. The current rating drops after a loss and would shift the expectation                       |
| Expected score E   | Empirical table: mean score by class, colour and 25-point band of rating difference (reference − opponent), estimated on the first games of sessions                                          | Lichess uses Glicko-2: the theoretical Elo formula is not calibrated on these data                                                         |
| Residual           | Score (1, ½, 0) − E                                                                                                                                                                           | Primary outcome: available for all games, not only the 8% with evaluations                                                                 |
| Move loss          | Drop in the mover's win probability between the evaluation before and after the move: Win% = 50 + 50 × (2 / (1 + e^(−0.00368 × cp)) − 1), with cp capped at ±1000 and mate = ±1000            | Lichess scale; gives little weight to errors in positions that are already decided                                                         |
| Error              | Inaccuracy from 5 pp of loss, mistake from 10, blunder from 15                                                                                                                                | Current Lichess thresholds (to be checked in the source code). The ?!, ?, ?? symbols in 2017 PGNs follow different rules: they are ignored |
| Remaining time     | The mover's clock after their previous move                                                                                                                                                   | It is the time available when they start thinking                                                                                          |
| Stable rating      | At least 50 valid games in the class in the month and median absolute rating change of at most 15 points                                                                                      | New ratings move by 25 points or more per game: the expectation is not reliable                                                            |
| Rating bands       | < 1400, 1400–1599, 1600–1799, 1800–1999, ≥ 2000 (reference rating)                                                                                                                            | 10th, 50th and 90th percentiles at about 1283, 1646 and 2003                                                                               |

## 3. Data and sample

- May 2017: 11,693,919 games, 228,525 players. Games with evaluations are 8.2% (957,369), not 6%.
- **New streaming pass** over the `.pgn.zst` file (estimate: 15–30 minutes): for each game and colour, the first clock, the clock after the tenth move, the last clock and the number of moves. `partite.parquet` does not contain the clocks of games without evaluations, and they are needed for the estimated end, playing pace and photo-finish endings. The first clock also reveals berserk (time halved in tournaments).
- Sessions are built from all games; primary outcomes are non-tournament bullet, blitz or rapid games of players with a stable rating.
- Each game counts as an outcome for one player only, chosen with a hash of the `game_id`: the two rows of the same game have opposite residuals, and keeping both would bias the standard errors.
- **Exploration and confirmation**: 20% of players (hash of the username) is used to develop and debug the code; the remaining 80% is analysed only once, with frozen code.
- DuckDB with `memory_limit` at 5 GB and an on-disk temporary directory; always `ORDER BY start_utc, game_id`.

## 4. Method, question 1 (tilt)

τ = mean residual after a loss − mean residual after a win (draws treated separately).

1. **Estimator A, between sessions.** From each residual I subtract the mean of the same player's residuals in all _other_ sessions: the player is compared with themselves. It still contains the "bad day" (low form that causes both the loss and the poor next game), so it is an upper bound of tilt.
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

| Risk                                           | Countermeasure                                                                                                          |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Wrong estimated end                            | Negative breaks expected below 1%; the histogram of the log break should have two humps with the valley near 30 minutes |
| The `.pgn.zst` file is no longer on disk       | Re-download it (a few GB) before phase 2                                                                                |
| 8 GB of RAM                                    | Only SQL aggregates and numpy on per-player sums; no heavy regression library                                           |
| May 2017 does not represent today              | Code parametrised by month; replication on a recent month after the deadline                                            |
| Unstable ratings, duplicate accounts, cheaters | Stability filter; the rest is noise unrelated to the previous outcome                                                   |
| Time and quota                                 | Cut order: H4, H3, causal check 2, question 2                                                                           |

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
- **Now**: regression, with block fixed effects, of the residual y(t) on the residual y(t−1), i.e. on the _unexpected_ result of the previous game (score − expected). I report τ = −slope: between a loss and a win the residual changes by one point, so τ still reads as "after a loss − after a win".
- **Why**: the within-session loss/win comparison is biased by the pairing system. If I win, my rating goes up, I face stronger opponents and lose more often _afterwards_: wins and losses are not exchangeable even without tilt, and shuffling does not correct this. The residual already accounts for the opponent's strength.
- **Evidence**: on simulated data without tilt, the plan's version gives −1.06 pp (95% CI −1.74 to −0.43), the new one −0.01 pp (−0.66 to 0.68). Two other seeds, two-sided: +0.07 and −0.05 pp (standard error 0.21).
- The plan's version remains in the output, labelled as biased, for transparency.

### P2. Bias correction: division by (1 − b)

- **Plan**: corrected τ = observed τ − mean of the shuffles (b).
- **Now**: τ_B = (observed τ − b) / (1 − b).
- **Why**: the short-sequence bias also shrinks a true effect towards zero, by the factor (1 − b). With b between 0.11 and 0.16, subtraction alone underestimates the effect by 11–16%.
- **Evidence**: simulated Markov chain with a true τ of −2.00 and −5.00 pp: subtraction gives −1.67 and −4.15; with the division −2.00 and −4.94. With the full chain of scripts and a 30-Elo tilt (about −4.0 pp): τ_B = −3.86 pp (95% CI −4.55 to −3.17).

### P3. Shuffles: within the block, last game fixed

- **Plan**: shuffle the order of games within each session.
- **Now**: shuffle within each _block_, keeping the last game of the block in last position.
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
- Baseline for pairs spanning two sessions (negative control): it excludes _both_ sessions, because the earlier one contains the game that defines the condition (otherwise there is about +1 pp of mechanical bias with 100 games).

### P7. Operational definition of the confirmatory tests

| Hypothesis | Statistic                                                                               | Test                                                   |
| ---------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| H1a        | τ_B, all classes, game +1                                                               | Permutation; decision with the 1 pp rule on the 95% CI |
| H1b        | τ_B(+1) − τ_B(+2), i.e. effect of the previous game minus effect of the game two before | Bootstrap over players, normal p                       |
| H1c        | τ_B bullet − τ_B rapid                                                                  | Bootstrap over players, normal p                       |
| H1d        | Slope of τ_B per +200 points of reference rating                                        | Permutation                                            |

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
  - z_d = x_d − mean result of the _distant_ games (at least 4 places before t) in the same block and of the same selection type as the game d places earlier (types are defined in P11);
  - the coefficients b_1, b_2, b_3 jointly solve Σ_t y_t z_d = Σ_k b_k Σ_t x_k z_d (d = 1, 2, 3); τ(+d) = −b_d.

  This is the regression of y_t on the three previous results, in which the deviation from the distant games acts as an instrument: b_d is the effect of the result d games earlier, holding the other two fixed. No shuffles and no (1 − b) correction are needed, because z uses only games before t (no mean containing y_t) and imposes no condition on what happens after t.

- **H1b test** (replaces the corresponding row of P7): τ(+1) − τ(+2) from the joint estimate; bootstrap over players, normal p, as in P7.
- **Assumption and cost**: after 3 games the effect is over; only outcomes with at least 4 previous games in the block count (blocks of 5 games or more). In simulation the standard error at +1 is 0.42, against 0.32 for estimator B; with many rematches, 0.65 against 0.45.
- The separate regressions remain in the output, labelled as biased.

| Simulated scenario                       | Seeds | Joint +1     | +2           | +3           | H1b          | Separate +2 (P7) |
| ---------------------------------------- | ----- | ------------ | ------------ | ------------ | ------------ | ---------------- |
| No tilt                                  | 7     | −0.06 ± 0.22 | 0.07 ± 0.16  | 0.18 ± 0.15  | −0.13 ± 0.22 | −0.24 ± 0.19     |
| Tilt 30 (−3.9 at +1)                     | 7     | −3.73 ± 0.15 | 0.18 ± 0.19  | 0.29 ± 0.15  | −3.92 ± 0.24 | **+0.88 ± 0.13** |
| Tilt 30 and tilt2 15 (−3.9 and −1.95)    | 7     | −4.01 ± 0.28 | −1.73 ± 0.11 | 0.02 ± 0.18  | −2.28 ± 0.32 | −1.10 ± 0.09     |
| No tilt, "realistic" rematches (see P11) | 4     | −0.20 ± 0.19 | 0.05 ± 0.34  | −0.12 ± 0.09 | −0.25 ± 0.20 | −0.13 ± 0.24     |
| Tilt 30, "realistic" rematches           | 4     | −3.87 ± 0.26 | 0.10 ± 0.25  | −0.42 ± 0.25 | −3.98 ± 0.40 | **+1.08 ± 0.28** |

Seed 1, as in the check that found the problem: `--tilt 30` → +1 −3.89 (95% CI −4.66 to −3.13), +2 **+0.60 (−0.29 to 1.41)**, +3 −0.15, H1b −4.49; `--tilt 30 --tilt2 15` → +1 −4.87 (−5.69 to −4.00), +2 −1.69 (−2.55 to −0.80), +3 −0.28, H1b −3.17. Over 11 scenarios and 55 simulations, the spread of the estimates across seeds is in line with the bootstrap standard error (ratios between 0.88 and 1.18).

### P11. Shuffles: fixed structure, swaps within the selection type (replaces P3)

- **P3**: shuffle the order of games within the block, last game fixed. In the code, each game moved together with its attributes (whether it is a rematch, whether it is the chosen side).
- **Problem**: rematches do not serve as outcomes and come in streaks. Which games enter the regression is a _structure_ of the block, and the short-sequence bias depends on that structure (on how many games serve both as previous game and as outcome). Moving games together with their attributes scatters the rematches, so the structure of the shuffles is no longer the true one and b is underestimated. Evidence, **without any tilt**, with streaks of rematches (probability 0.75 of another rematch after a rematch), code of the previous commit: τ_B = +1.47, +1.26, +1.42, +0.89 over four seeds (mean **+1.26**; all four 95% CIs exclude zero, permutation p 0.005). If, in addition, a rematch is more likely after a loss (0.40 against 0.12): mean **+2.0**. In the real data, rematches make up between 26% (rapid) and 50% (bullet) of the pairs within blocks (`06_diagnostiche.txt`): the primary estimator would have had a positive bias, capable of hiding a tilt or of simulating a rebound.
- **Now**:
  1. the structure stays fixed: which games are rematches, which serve as outcomes, which is the last. Only the results (y and score) are swapped;
  2. a result can only move to the place of a game of the same **selection type**: what follows the game (a different opponent, a rematch, the end of the block) × whether the game itself is a rematch. Stopping and asking for a rematch depend on the result just obtained: this is the same reason as the "last game fixed" of P3, extended to rematches. With `--rivincite`, only "last" counts.
  - The `rim_libero` column swaps results among all games of the block, with the structure fixed: if it differs, the selection rules matter. The script also prints the probability of a rematch after a loss and after a win.
- The observed statistic does not change; b and the permutation p-values of H1a and H1d do.
- **Rule for H1a**: it stays on τ_B. If the joint estimate at +1 (P10) leads to a different verdict under the 1 pp rule, I report both and the verdict is "inconclusive".

| Simulated scenario                                                                           | Seeds | τ_B, previous commit | τ_B, now     | `rim_libero` |
| -------------------------------------------------------------------------------------------- | ----- | -------------------- | ------------ | ------------ |
| No tilt                                                                                      | 7     | —                    | 0.14 ± 0.17  | 0.11 ± 0.15  |
| No tilt, streaks of rematches (0.75)                                                         | 4     | **+1.26**            | 0.04 ± 0.13  | 0.01 ± 0.08  |
| No tilt, streaks and rematch after a loss (0.40)                                             | 4     | **+2.01**            | −0.34 ± 0.27 | −0.11 ± 0.26 |
| No tilt, rematch after a loss (0.60), no streaks                                             | 9     | —                    | 0.04 ± 0.14  | 0.00 ± 0.16  |
| No tilt, "realistic": streaks, rematch after a loss 0.40, opponent keeps their true strength | 4     | —                    | 0.10 ± 0.16  | 0.24 ± 0.14  |
| Tilt 30 (−3.9)                                                                               | 7     | —                    | −3.71 ± 0.09 | −3.76 ± 0.09 |
| Tilt 30, "realistic"                                                                         | 4     | —                    | −3.39 ± 0.13 | −3.57 ± 0.18 |
| Tilt 30 and tilt2 15                                                                         | 7     | —                    | −3.35 ± 0.15 | −3.43 ± 0.14 |

- **Measured limitations** (all conservative, i.e. towards zero): τ_B is shrunk by 5% in the base simulator and by 13% in the realistic scenario (the (1 − b) correction is approximate, and swapping within type conditions on what follows the outcome game); by 14% if the effect lasts two games, because B assumes it lasts one. The joint estimate at +1 does not have these limitations (−3.87 and −4.01 in the same scenarios) but is less precise.
- Unmeasured limitation: if stopping or asking for a rematch depends on more than the last result (for example on two losses in a row), the types are not enough.
- New options in `tests/simula_dati.py` for these checks: `--rivincita-sconfitta`, `--rivincita-catena`, `--avversario-stabile`, `--verita`.

### P12. Evaluated sample: the verdict of check 2 is read within the player

Written after reading `09_controlli_eval_esplorazione.txt`; it does not concern any confirmatory test.

- **Plan (section 7)**: "by player: does the probability that a game was analysed depend on the outcome of the previous game or on its own result?", with a threshold of 10% relative.
- **Problem**: the script printed the verdict on the shares of all players pooled (table 2a). For "the game's own result" that comparison cannot say anything: every decided game has a winner and a loser, so the two shares are equal by construction (8.36% and 8.38%).
- **Now**: the verdict uses the within-player comparison (table 2b). On the exploration group: outcome of the previous game 13.19% against 14.24%, i.e. −7.4% (within the threshold); the game's own result 12.59% against 16.24%, i.e. **−22.5% (beyond the threshold)**: among players whose games are only sometimes analysed, won games are analysed more often than lost ones.
- **Consequence**, following the plan's rule: errors "after a loss" are not measured on Lichess evaluations, except for systematic analysers (89 players, 2.2% of analysed games) and with plan B (local Stockfish). This concerns H3 and the exploratory analysis of the type of loss, both outside this sprint. Question 1 uses the score of all games and is unaffected. Question 2 compares moves within the same game: it remains valid, but it applies to a sample in which 2017 "Classical" makes up 35.6% (against 23.0% among non-analysed games) and draws are analysed less often (5.3% against 8.4% of decided games): its curves must be read by class.
