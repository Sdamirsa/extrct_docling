# Figure data: pictures_14 of AMIE-Mx (page 21)

> **Machine-read from the figure.** Nothing here is taken from the paper's text or tables, and none of it was checked by a person.
> Method `agent` (an agent session on this figure), model `gemma4:26b-a4b-it-qat`, 2026-11-18, figure-to-data step 3.
> Values can be wrong or missing: check them against `figure.png` before relying on them.

**Caption in the paper:** Extended Data Fig. 7 | Patient actor ratings. Conversation qualities as assessed by patient actors upon conclusion of the consultation. For illustration purposes, all responses from five-point rating scales were mapped to a generic five-point scale ranging from 'Very favorable' to 'Very unfavorable'. For Yes/No questions, a (positive) 'Yes' response was mapped to the same color as 'Favorable' and a (negative) 'No' response to the same color as 'Unfavorable'.

## Chart 1: GMCPQ (bar)

x axis linear 20 to 100; y axis categorical.

| category | x | series | value | low | high | printed | from | confidence |
|---|---|---|---|---|---|---|---|---|
| Being Polite | 1 | Very favorable | 55* |  |  |  | agent | 0.5 |
| Being Polite | 2 | Favorable | 40* |  |  |  | agent | 0.5 |
| Being Polite | 3 | Unfavorable | 5* |  |  |  | agent | 0.5 |
| Making Patient Feel At Ease | 1 | Very favorable | 45* |  |  |  | agent | 0.5 |
| Making Patient Feel At Ease | 2 | Favorable | 25* |  |  |  | agent | 0.5 |
| Making Patient Feel At Ease | 3 | Neither | 25* |  |  |  | agent | 0.5 |
| Making Patient Feel At Ease | 4 | Unfavorable | 5* |  |  |  | agent | 0.5 |
| Listening to Patient | 1 | Very favorable | 50* |  |  |  | agent | 0.5 |
| Listening to Patient | 2 | Favorable | 30* |  |  |  | agent | 0.5 |
| Listening to Patient | 3 | Neither | 15* |  |  |  | agent | 0.5 |
| Listening to Patient | 4 | Unfavorable | 5* |  |  |  | agent | 0.5 |
| Assessing Medical Condition | 1 | Very favorable | 50* |  |  |  | agent | 0.5 |
| Assessing Medical Condition | 2 | Favorable | 20* |  |  |  | agent | 0.5 |
| Assessing Medical Condition | 3 | Neither | 20* |  |  |  | agent | 0.5 |
| Assessing Medical Condition | 4 | Unfavorable | 5* |  |  |  | agent | 0.5 |
| Assessing Medical Condition | 5 | Very unfavorable | 5* |  |  |  | agent | 0.5 |
| Explaining Condition and Treatment | 1 | Very favorable | 75* |  |  |  | agent | 0.5 |
| Explaining Condition and Treatment | 2 | Favorable | 10* |  |  |  | agent | 0.5 |
| Explaining Condition and Treatment | 3 | Unfavorable | 15* |  |  |  | agent | 0.5 |
| Involving Patient in Treatment Decisions | 1 | Very favorable | 65* |  |  |  | agent | 0.5 |
| Involving Patient in Treatment Decisions | 2 | Favorable | 25* |  |  |  | agent | 0.5 |
| Involving Patient in Treatment Decisions | 3 | Unfavorable | 10* |  |  |  | agent | 0.5 |
| Providing Appropriate Treatment Plan | 1 | Very favorable | 70* |  |  |  | agent | 0.5 |
| Providing Appropriate Treatment Plan | 2 | Favorable | 15* |  |  |  | agent | 0.5 |
| Providing Appropriate Treatment Plan | 3 | Neither | 10* |  |  |  | agent | 0.5 |
| Providing Appropriate Treatment Plan | 4 | Unfavorable | 5* |  |  |  | agent | 0.5 |
| Patient Trusts Information is Confidential | 1 | Very favorable | 80* |  |  |  | agent | 0.5 |
| Patient Trusts Information is Confidential | 2 | Favorable | 5* |  |  |  | agent | 0.5 |
| Patient Trusts Information is Confidential | 3 | Unfavorable | 10* |  |  |  | agent | 0.5 |
| Patient Trusts Information is Confidential | 4 | Cannot rate / Does not apply | 5* |  |  |  | agent | 0.5 |
| Appearing Honest And Trustworthy | 1 | Very favorable | 75* |  |  |  | agent | 0.5 |
| Appearing Honest And Trustworthy | 2 | Favorable | 5* |  |  |  | agent | 0.5 |
| Appearing Honest And Trustworthy | 3 | Neither | 5* |  |  |  | agent | 0.5 |
| Appearing Honest And Trustworthy | 4 | Unfavorable | 5* |  |  |  | agent | 0.5 |
| Appearing Honest And Trustworthy | 5 | Very unfavorable | 5* |  |  |  | agent | 0.5 |
| Appearing Honest And Trustworthy | 6 | Cannot rate / Does not apply | 5* |  |  |  | agent | 0.5 |
| Patient Confident About Care Provided (Y/N) | 1 | Favorable | 85* |  |  |  | agent | 0.5 |
| Patient Confident About Care Provided (Y/N) | 2 | Very favorable | 5* |  |  |  | agent | 0.5 |
| Patient Confident About Care Provided (Y/N) | 3 | Very unfavorable | 5* |  |  |  | agent | 0.5 |
| Patient Confident About Care Provided (Y/N) | 4 | Cannot rate / Does not apply | 5* |  |  |  | agent | 0.5 |
| Patient Happy to Return In Future (Y/N) | 1 | Favorable | 80* |  |  |  | agent | 0.5 |
| Patient Happy to Return In Future (Y/N) | 2 | Very favorable | 10* |  |  |  | agent | 0.5 |
| Patient Happy to Return In Future (Y/N) | 3 | Unfavorable | 5* |  |  |  | agent | 0.5 |
| Patient Happy to Return In Future (Y/N) | 4 | Cannot rate / Does not apply | 5* |  |  |  | agent | 0.5 |

- Note: Horizontal stacked bar chart. Segments are stacked in the order they appear in the data: Very favorable (Red), Favorable (Blue), Neither (Light Blue), Unfavorable (Light Grey), Very unfavorable (Dark Grey), Cannot rate (Lightest Grey). The order of segments in each bar seems to depend on which categories have non-zero values, starting from Very favorable if it exists, then Favorable, etc. Wait, actually, looking at 'Patient Happy...', it starts with Favorable. Let's re-examine. Actually, if 'Being Polite' starts with Red, it's Very favorable. If 'Patient Happy...' starts with Blue, it's Favorable. It seems they stack from most favorable to least favorable? If so, 'Being Polite' should start with Very Favorable (Red). 'Patient Happy...' should start with Very Favorable (Red). But 'Patient Happy...' starts with Blue. This means they are stacking in the order of categories: Favorable, Very favorable? No, that's weird. Let's look at 'Patient Happy...' again. Is it Red then Blue? No, it's Blue then Red. So it's Favorable (Blue) then Very favorable (Red). This is the reverse of 'Being Polite' which is Red then Blue. This is very confusing. I will just read what I see.

`*` marks a value whose confidence is under 0.7: it failed a check (see Checks) or was not confirmed by anything printed in the figure. Such values are left out of the table embedded in the paper's exports.

## Checks

- agent session: stopped after 300 s
- the session ended before finish: what was recorded is kept

Column `from`: `printed` a number printed in the figure; `vector` measured on the PDF's drawing by code; `raster` measured on the pixels at a mark the model pointed to; `vlm`, `agent` the model's own reading against the axis.

---
Same record for programs: `figure-to-data.json` (`extrct.figure-data/1`). What the reader was given: `figure.png`, `figure.txt`. How it was run: `../runs/20261118-114914_agent_gemma4-26b-a4b-it-qat.json`.
