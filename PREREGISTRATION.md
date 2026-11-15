# Tilt — Research plan and pre-registration (v1.2)

Written on 15 November 2026, before any analysis of outcomes: so far only descriptive counts have been examined (`riassunto_dati.txt`, `statistiche_campione.txt`). Committed to GitHub before phase 3: the commit date shows that the hypotheses precede the results.

_This is a faithful English translation of the original Italian plan (`PIANO_RICERCA_it.md`, v1), committed together with it. Section 11 records the amendments agreed after v1 was written and before any outcome analysis. Section 12 records the clarifications made at the end of phase 2, after testing the code on simulated data and before running any script on the real data (Italian original: `PRECISAZIONI_it.md`)._

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
