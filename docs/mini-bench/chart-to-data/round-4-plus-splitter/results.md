# Split check: results

51 figures, 236 charts. Made by `scripts/score.py`; the README says what the columns mean.

## Each splitter alone

| Splitter | Figures cut right | Bench | Showcase paper | Other papers | Right chart count | Charts found | Whole in its box | Extra boxes | Seconds | USD |
|---|---|---|---|---|---|---|---|---|---|---|
| Rule splitter (today) | **24 of 51** | 9 of 10 | 5 of 11 | 10 of 30 | 26 | 165 of 236 | 135 | 54 | 0 |  |
| Heron, boxes as they are | **24 of 51** | 5 of 10 | 10 of 11 | 9 of 30 | 26 | 126 of 236 | 92 | 29 | 6 |  |
| Heron, then the rules' cut | **24 of 51** | 5 of 10 | 10 of 11 | 9 of 30 | 26 | 114 of 236 | 106 | 41 | 6 |  |
| FigEx2 detector alone | **16 of 51** | 3 of 10 | 5 of 11 | 8 of 30 | 16 | 61 of 236 | 58 | 22 | 8 |  |
| FigEx2 detector, guided | **18 of 51** | 3 of 10 | 6 of 11 | 9 of 30 | 18 | 64 of 236 | 61 | 22 | 8 |  |
| FigEx2 as designed | **24 of 51** | 5 of 10 | 7 of 11 | 12 of 30 | 37 | 95 of 236 | 89 | 66 | 402 |  |
| Gemma 4 26B (local) | **28 of 51** | 7 of 10 | 8 of 11 | 13 of 30 | 42 | 124 of 236 | 53 | 103 | 281 |  |
| Sonnet 5.5 (cloud) | **49 of 51** | 10 of 10 | 11 of 11 | 28 of 30 | 51 | 218 of 236 | 145 | 18 | 170 | 0.5347 |
| Gemini 3.8 Flash (cloud) | **49 of 51** | 10 of 10 | 11 of 11 | 28 of 30 | 50 | 234 of 236 | 134 | 4 | 272 | 0.1593 |
| Gemma, then the rules' cut | **32 of 51** | 8 of 10 | 8 of 11 | 16 of 30 | 42 | 152 of 236 | 119 | 75 | 281 |  |
| Sonnet, then the rules' cut | **47 of 51** | 10 of 10 | 11 of 11 | 26 of 30 | 51 | 214 of 236 | 188 | 22 | 170 | 0.5347 |
| Gemini, then the rules' cut | **47 of 51** | 10 of 10 | 11 of 11 | 26 of 30 | 50 | 230 of 236 | 220 | 8 | 272 | 0.1593 |

## With Heron as judge

| Splitter | Alone | With the judge | They agree on the count | Right when they agree | They differ | Splitter right | Judge right |
|---|---|---|---|---|---|---|---|
| Rule splitter (today) | 24 | **24** | 20 | 16 | 31 | 8 | 8 |
| Heron, then the rules' cut | 24 | **24** | 51 | 24 | 0 | 0 | 0 |
| FigEx2 detector alone | 16 | **24** | 20 | 11 | 31 | 5 | 13 |
| FigEx2 detector, guided | 18 | **24** | 20 | 12 | 31 | 6 | 12 |
| FigEx2 as designed | 24 | **22** | 22 | 17 | 29 | 7 | 5 |
| Gemma 4 26B (local) | 28 | **20** | 25 | 18 | 26 | 10 | 2 |
| Sonnet 5.5 (cloud) | 49 | **26** | 26 | 26 | 25 | 23 | 0 |
| Gemini 3.8 Flash (cloud) | 49 | **26** | 26 | 26 | 25 | 23 | 0 |
| Gemma, then the rules' cut | 32 | **22** | 25 | 20 | 26 | 12 | 2 |
| Sonnet, then the rules' cut | 47 | **25** | 26 | 25 | 25 | 22 | 0 |
| Gemini, then the rules' cut | 47 | **25** | 26 | 25 | 25 | 22 | 0 |

## With FigEx2 as judge

| Splitter | Alone | With the judge | They agree on the count | Right when they agree | They differ | Splitter right | Judge right |
|---|---|---|---|---|---|---|---|
| Rule splitter (today) | 24 | **31** | 20 | 20 | 31 | 4 | 11 |
| Heron, boxes as they are | 24 | **26** | 22 | 19 | 29 | 5 | 7 |
| Heron, then the rules' cut | 24 | **26** | 22 | 19 | 29 | 5 | 7 |
| FigEx2 detector alone | 16 | **25** | 17 | 13 | 34 | 3 | 12 |
| FigEx2 detector, guided | 18 | **25** | 19 | 15 | 32 | 3 | 10 |
| Gemma 4 26B (local) | 28 | **25** | 39 | 24 | 12 | 4 | 1 |
| Sonnet 5.5 (cloud) | 49 | **37** | 37 | 37 | 14 | 12 | 0 |
| Gemini 3.8 Flash (cloud) | 49 | **37** | 36 | 36 | 15 | 13 | 1 |
| Gemma, then the rules' cut | 32 | **29** | 39 | 28 | 12 | 4 | 1 |
| Sonnet, then the rules' cut | 47 | **37** | 37 | 37 | 14 | 10 | 0 |
| Gemini, then the rules' cut | 47 | **37** | 36 | 36 | 15 | 11 | 1 |

## A model's count choosing between the rules' cut and Heron's

| Count from | Its count is right | Figures cut right | Bench | Showcase paper | Other papers | Took the rules' cut (right) | Took Heron's (right) | Took its own boxes (right) |
|---|---|---|---|---|---|---|---|---|
| Gemma 4 26B (local) | 42 | **35 of 51** | 10 of 10 | 10 of 11 | 15 of 30 | 22 (22) | 10 (7) | 19 (6) |
| Sonnet 5.5 (cloud) | 51 | **46 of 51** | 10 of 10 | 11 of 11 | 25 of 30 | 26 (24) | 10 (8) | 15 (14) |
| Gemini 3.8 Flash (cloud) | 50 | **46 of 51** | 10 of 10 | 11 of 11 | 25 of 30 | 26 (24) | 10 (8) | 15 (14) |
| FigEx2 captioning model | 38 | **31 of 51** | 8 of 10 | 9 of 11 | 14 of 30 | 20 (20) | 9 (6) | 22 (5) |

## Chart count per figure

| Figure | Has | Rule splitter (today) | Heron, boxes as they are | Heron, then the rules' cut | FigEx2 detector alone | FigEx2 detector, guided | FigEx2 as designed | Gemma 4 26B (local) | Sonnet 5.5 (cloud) | Gemini 3.8 Flash (cloud) | Gemma, then the rules' cut | Sonnet, then the rules' cut | Gemini, then the rules' cut |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A3 | 1 | 1 | 1 | 1 | 1 | 1 | 3 ✗ | 1 | 1 | 1 | 1 | 1 | 1 |
| B1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| B2 | 3 | 3 | 3 | 3 | 1 ✗ | 1 ✗ | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| B3 | 5 | 5 | 1 ✗ | 1 ✗ | 1 ✗ | 1 ✗ | 5 ~ | 5 ~ | 5 | 5 | 5 ~ | 5 | 5 |
| B4 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| B5 | 10 | 10 | 2 ✗ | 2 ✗ | 2 ✗ | 2 ✗ | 2 ✗ | 10 ~ | 10 | 10 | 10 ~ | 10 | 10 |
| C1 | 4 | 4 | 1 ✗ | 1 ✗ | 1 ✗ | 1 ✗ | 4 ~ | 4 | 4 | 4 | 4 | 4 | 4 |
| C3 | 3 | 3 | 8 ✗ | 8 ✗ | 1 ✗ | 1 ✗ | 3 ~ | 3 | 3 | 3 | 3 | 3 | 3 |
| C4 | 2 | 1 ✗ | 1 ✗ | 1 ✗ | 1 ✗ | 1 ✗ | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| C5 | 3 | 3 | 3 | 3 | 1 ✗ | 1 ✗ | 3 | 3 ~ | 3 | 3 | 3 | 3 | 3 |
| S02 | 4 | 4 | 4 | 4 | 3 ✗ | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| S03 | 1 | 2 ✗ | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| S04 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| S05 | 2 | 2 | 1 ✗ | 1 ✗ | 2 | 2 | 2 | 2 ~ | 2 | 2 | 2 ~ | 2 | 2 |
| S06 | 4 | 6 ✗ | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| S08 | 1 | 3 ✗ | 1 | 1 | 1 | 1 | 5 ✗ | 1 | 1 | 1 | 1 | 1 | 1 |
| S10 | 3 | 3 | 3 | 3 | 2 ✗ | 2 ✗ | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| S11 | 11 | 7 ✗ | 11 | 11 | 1 ✗ | 1 ✗ | 6 ✗ | 8 ✗ | 11 | 11 | 8 ✗ | 11 | 11 |
| S12 | 5 | 1 ✗ | 5 | 5 | 2 ✗ | 1 ✗ | 5 ~ | 5 | 5 | 5 | 5 | 5 | 5 |
| S13 | 4 | 4 | 4 | 4 | 1 ✗ | 1 ✗ | 4 ~ | 4 ~ | 4 | 4 | 4 ~ | 4 | 4 |
| S14 | 3 | 8 ✗ | 3 | 3 | 2 ✗ | 2 ✗ | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| W01 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| W02 | 3 | 3 ~ | 2 ✗ | 2 ✗ | 1 ✗ | 1 ✗ | 2 ✗ | 4 ✗ | 3 | 3 | 4 ✗ | 3 | 3 |
| W03 | 2 | 2 | 1 ✗ | 1 ✗ | 1 ✗ | 2 | 2 | 1 ✗ | 2 | 2 | 1 ✗ | 2 | 2 |
| W04 | 15 | 16 ✗ | 1 ✗ | 1 ✗ | 1 ✗ | 1 ✗ | 7 ✗ | 25 ✗ | 15 | 15 | 25 ✗ | 15 | 15 |
| W05 | 17 | 17 ~ | 3 ✗ | 3 ✗ | 1 ✗ | 1 ✗ | 4 ✗ | 20 ✗ | 17 ~ | 17 ~ | 20 ✗ | 17 ~ | 17 ~ |
| W06 | 15 | 6 ✗ | 1 ✗ | 1 ✗ | 1 ✗ | 1 ✗ | 2 ✗ | 20 ✗ | 15 ~ | 15 | 20 ✗ | 15 ~ | 15 |
| W07 | 2 | 1 ✗ | 1 ✗ | 1 ✗ | 2 | 2 | 2 | 2 | 2 | 4 ✗ | 2 | 2 | 4 ✗ |
| W08 | 3 | 3 | 2 ✗ | 2 ✗ | 3 | 3 | 3 ~ | 3 | 3 | 3 | 3 | 3 | 3 |
| W09 | 2 | 5 ✗ | 5 ✗ | 5 ✗ | 3 ✗ | 3 ✗ | 3 ✗ | 3 ✗ | 2 | 2 | 3 ✗ | 2 | 2 |
| W10 | 14 | 11 ✗ | 14 ~ | 14 ~ | 4 ✗ | 5 ✗ | 6 ✗ | 14 ~ | 14 | 14 | 14 ~ | 14 ~ | 14 ~ |
| W11 | 1 | 3 ✗ | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| W12 | 2 | 3 ✗ | 1 ✗ | 1 ✗ | 2 | 2 | 2 | 2 ~ | 2 | 2 | 2 | 2 | 2 |
| W13 | 2 | 2 | 2 | 2 | 1 ✗ | 1 ✗ | 2 | 2 ~ | 2 | 2 | 2 | 2 | 2 |
| W14 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| W15 | 12 | 12 | 12 | 12 | 1 ✗ | 1 ✗ | 2 ✗ | 2 ✗ | 12 | 12 | 2 ✗ | 12 | 12 |
| W16 | 18 | 16 ✗ | 13 ✗ | 13 ✗ | 3 ✗ | 3 ✗ | 3 ✗ | 3 ✗ | 18 | 18 | 3 ✗ | 18 ~ | 18 ~ |
| W17 | 4 | 4 | 3 ✗ | 3 ✗ | 1 ✗ | 1 ✗ | 4 ~ | 4 | 4 | 4 | 4 | 4 | 4 |
| W18 | 4 | 4 | 4 | 4 | 1 ✗ | 1 ✗ | 4 ~ | 4 | 4 | 4 | 4 | 4 | 4 |
| W19 | 3 | 2 ✗ | 3 | 3 | 2 ✗ | 2 ✗ | 3 | 3 ~ | 3 | 3 | 3 ~ | 3 | 3 |
| W20 | 2 | 1 ✗ | 1 ✗ | 1 ✗ | 1 ✗ | 1 ✗ | 2 ~ | 2 ~ | 2 | 2 | 2 ~ | 2 | 2 |
| W21 | 6 | 3 ✗ | 4 ✗ | 4 ✗ | 1 ✗ | 1 ✗ | 6 ~ | 6 | 6 | 6 | 6 | 6 | 6 |
| W22 | 1 | 1 | 1 | 1 | 1 | 1 | 2 ✗ | 1 | 1 | 1 | 1 | 1 | 1 |
| W23 | 4 | 8 ✗ | 3 ✗ | 3 ✗ | 1 ✗ | 1 ✗ | 4 ~ | 4 ~ | 4 | 4 | 4 | 4 | 4 |
| W24 | 2 | 2 | 2 | 2 | 1 ✗ | 1 ✗ | 2 | 2 ~ | 2 | 2 | 2 ~ | 2 | 2 |
| W25 | 4 | 6 ✗ | 3 ✗ | 3 ✗ | 2 ✗ | 2 ✗ | 2 ✗ | 4 | 4 | 4 | 4 | 4 | 4 |
| W26 | 6 | 2 ✗ | 1 ✗ | 1 ✗ | 4 ✗ | 5 ✗ | 6 | 6 ~ | 6 | 6 | 6 ~ | 6 | 6 |
| W27 | 5 | 2 ✗ | 5 ~ | 5 ~ | 3 ✗ | 3 ✗ | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| W28 | 3 | 4 ✗ | 1 ✗ | 1 ✗ | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| W29 | 5 | 2 ✗ | 1 ✗ | 1 ✗ | 2 ✗ | 2 ✗ | 5 ~ | 5 | 5 | 5 | 5 | 5 | 5 |
| W30 | 4 | 2 ✗ | 1 ✗ | 1 ✗ | 1 ✗ | 1 ✗ | 4 ~ | 4 ~ | 4 | 4 | 4 ~ | 4 | 4 |

✗: wrong number of charts. ~: right number, but a chart is not found (a box in the wrong place).
