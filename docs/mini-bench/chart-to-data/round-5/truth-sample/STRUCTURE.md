# Structure of the five figures

What `#/pictures/10` to `#/pictures/14` of `Public-test-manuscript` hold, counted on the bitmap embedded in each PDF page (the bundle crop is the same bitmap at 0.49 px per px). Written on 2026-11-19 by the agent that made the sample truth in this folder (`claude-fable-5-2`), from the figures alone: no model output and no VLM description was read.

## Common to every panel of the five figures

- **Bars:** 37 per panel, one vertical stacked bar per model, in groups of 6, 7, 4, 13, 5 and 2 separated by an empty slot (found in all 26 panels: by the gaps between the bars in 25, by eye in the IBS panel of picture 11, where a label box hides the foot of bar 36).
- **Segment classes (legend, top right inside the plot area):** Correct, 2OP, EOP, NOP, Error, Incorrect. Stacked in that order from the bottom; every bar sums to 100 %. EOP is drawn in the colour of the plot background.
- **y axis:** `Percentage`, tick labels 0, 20, 40, 60, 80, 100 (the axis line runs on to 105; to 100 in one panel, noted below).
- **Printed share:** the share of Correct is printed as `dd.d%` in a translucent box about 10.7 axis units under the top of the Correct segment. A bar whose Correct share is under about 8 % (and so a bar with 0) prints nothing: the label would fall under the axis. Labels of neighbouring bars overprint each other.
- **Values:** 37 bars x 6 classes = 222 segment values per panel, of which at most 37 are printed (Correct); the other five classes are never printed.
- **x tick labels (rotated 45 degrees), the same 37 in the same order in every panel, as printed:**

  - bars 1-6: `GPT-3.5 Web`, `GPT-3.5 API`, `GPT-4 Web`, `GPT-4 API`, `GPT-4o API`, `GPT-4omini API`
  - bars 7-13: `Claude3-Hiaku Web`, `Claude3-Haiku API`, `Claude3-Sonnet Web`, `Claude3-Sonnet API`, `Claude3-Opus Web`, `Claude3-Opus API`, `Claude3.5-Sonnet API`
  - bars 14-17: `Mistralv2-7b Poe`, `Mistralv2-7b-Q8 Local`, `Mistral-Large Poe`, `Mixtral-8x7b Poe`
  - bars 18-30: `Llama2-7b Poe`, `Llama2-7b-Q8 Local`, `medicineLLM-7b-Q8 Local`, `Llama2-13b Poe`, `Llama2-13b-Q5 Local`, `Llama2-70b Poe`, `Llama3-8b Poe`, `Llama3-8b-Q8 Local`, `OpenBioLLM-8b-Q8 Local`, `Llama3-70b Poe`, `Llama3.1-8b Poe`, `Llama3.1-70b Poe`, `Llama3.1-405b Poe`
  - bars 31-35: `Gemini Web`, `GeminiAdvanced Web`, `Gemma2-9b Poe`, `Gemma2-9b-Q8 Local`, `Gemma2-27b Poe`
  - bars 36-37: `Phi3-3b-Q16 Local`, `Phi3-14b-Q6 Local`

  Read in pictures 10 and 14 (every label legible) and in picture 13; in pictures 11 and 12 they are blurred but recognisable as the same names. `Claude3-Hiaku Web` is spelled that way in the figure.

## Per figure

| picture | page | panels | layout | bars per panel | segment values | Correct shares printed | digits of the printed share | bitmap |
|---|---|---|---|---|---|---|---|---|
| `#/pictures/10` | 62 | 3 | 3 rows x 1 column | 37 | 666 | 111 of 111 | 7 to 8 px high, legible | 1065 x 1597 px, lossless (FlateDecode) |
| `#/pictures/11` | 63 | 11 | 6 rows x 2 columns, the last row holds one panel (left) | 37 | 2442 | 403 of 407 | 4 to 5 px high, not legible | 1247 x 1855 px, lossless (FlateDecode) |
| `#/pictures/12` | 64 | 5 | 5 rows x 1 column | 37 | 1110 | 182 of 185 | about 5 px high, not legible | 547 x 1824 px, lossless (FlateDecode) |
| `#/pictures/13` | 65 | 4 | 4 rows x 1 column | 37 | 888 | 148 of 148 | 5 to 6 px high, not legible | 677 x 1805 px, JPEG (DCTDecode) |
| `#/pictures/14` | 66 | 3 | 3 rows x 1 column | 37 | 666 | 111 of 111 | about 7 px high, legible | 858 x 1715 px, JPEG (DCTDecode) |
| total | | 26 | | | 5772 | 955 of 962 | | |

## Legibility of the printed shares

One line per figure. Digit heights are in pixels of the bitmap embedded in the PDF (220 ppi); in the bundle crop (108 ppi) they are half that.

- `#/pictures/10`: legible. Digits 7 to 8 px high, lossless bitmap; every sampled share was read on enlargement and agrees with the bar top within 0.19. The sample truth holds the printed shares.
- `#/pictures/11`: not legible. Digits 4 to 5 px high, lossless bitmap; 3, 5, 6, 8, 9 and 0 cannot be told apart at 14x to 22x. The sample truth holds the Correct segment measured against the y axis instead (`source: "raster"`, +-0.3).
- `#/pictures/12`: not legible. Digits about 5 px high, lossless bitmap; 3, 5, 6, 8, 9 and 0 cannot be told apart at 14x to 22x. The sample truth holds the Correct segment measured against the y axis instead (`source: "raster"`, +-0.3).
- `#/pictures/13`: not legible. Digits 5 to 6 px high, JPEG bitmap; 3, 5, 6, 8, 9 and 0 cannot be told apart at 14x to 22x. The sample truth holds the Correct segment measured against the y axis instead (`source: "raster"`, +-0.3).
- `#/pictures/14`: legible. Digits about 7 px high, JPEG bitmap; every sampled share was read on enlargement and agrees with the bar top within 0.19. The sample truth holds the printed shares.

### `#/pictures/10` (page 62)

Supplementary Figure S4. Performance Stratified by Image-Inclusive and Text-Based Questions. 3 panels, 3 rows x 1 column. Titles as printed, in reading order:

1. `All 2022 ACG questions (N = 300)`
2. `Question type: text-based (N = 162)`
3. `Question type: image-inclusive (N = 138)`

Every bar prints its Correct share: 111 printed shares.
The digits of the printed shares are 7 to 8 px high in the PDF's bitmap and can be read there on enlargement (9x to 24x); in the bundle crop they are about half that.

### `#/pictures/11` (page 63)

Supplementary Figure S5. Performance Stratified by Question Subject. 11 panels, 6 rows x 2 columns, the last row holds one panel (left). Titles as printed, in reading order:

1. `Question type: COLON (N = 49)`
2. `Question type: ENDOSCOPY (N = 26)`
3. `Question type: ESOPHAGUS (N = 36)`
4. `Question type: IBD (N = 30)`
5. `Question type: IBS (N = 14)` - no share printed in: bar 23 `Llama2-70b Poe` (Correct is 1/14 = 7.1 %)
6. `Question type: LIVER (N = 52)`
7. `Question type: MISCELLANEOUS (N = 19)`
8. `Question type: NUTRITION (N = 3)` - no share printed in: bar 18 `Llama2-7b Poe` (Correct is 0); bar 19 `Llama2-7b-Q8 Local` (Correct is 0); bar 20 `medicineLLM-7b-Q8 Local` (Correct is 0)
9. `Question type: PANCREATICO-BILIARY (N = 31)`
10. `Question type: SMALL BOWEL (N = 22)`
11. `Question type: STOMACH (N = 17)`

Every bar prints its Correct share except the 4 listed above: 403 printed shares in 407 bars.
The digits of the printed shares are 4 to 5 px high in the PDF's bitmap (half that in the bundle crop) and cannot be read: single digits cannot be told apart. What these panels hold can only be measured against the y axis.

### `#/pictures/12` (page 64)

Supplementary Figure S6. Performance stratified by patient care phase. 5 panels, 5 rows x 1 column. Titles as printed, in reading order:

1. `Question type: Complication (N = 55)`
2. `Question type: Diagnosis (N = 123)`
3. `Question type: Investigation (N = 211)`
4. `Question type: Pathophisiology (N = 3)` - no share printed in: bar 2 `GPT-3.5 API` (Correct is 0); bar 14 `Mistralv2-7b Poe` (Correct is 0); bar 23 `Llama2-70b Poe` (Correct is 0) - this panel's axis ends at 100, not 105; the title is spelled `Pathophisiology`
5. `Question type: Treatment (N = 217)`

Every bar prints its Correct share except the 3 listed above: 182 printed shares in 185 bars.
The digits of the printed shares are about 5 px high in the PDF's bitmap (half that in the bundle crop) and cannot be read: single digits cannot be told apart. What these panels hold can only be measured against the y axis.

### `#/pictures/13` (page 65)

Supplementary Figure S7. Performance Stratified by Question Difficulty. 4 panels, 4 rows x 1 column. Titles as printed, in reading order:

1. `Question Difficulty (Average Human Score): Q1 (N = 75)`
2. `Question Difficulty (Average Human Score): Q2 (N = 75)`
3. `Question Difficulty (Average Human Score): Q3 (N = 75)`
4. `Question Difficulty (Average Human Score): Q4 (N = 75)`

Every bar prints its Correct share: 148 printed shares.
The digits of the printed shares are 5 to 6 px high in the PDF's bitmap (half that in the bundle crop) and cannot be read: single digits cannot be told apart. What these panels hold can only be measured against the y axis.

### `#/pictures/14` (page 66)

Supplementary Figure S8. Performance stratified by the question length. 3 panels, 3 rows x 1 column. Titles as printed, in reading order:

1. `Question type: Long (N = 99)`
2. `Question type: Medium (N = 99)`
3. `Question type: Short (N = 102)`

Every bar prints its Correct share: 111 printed shares.
The digits of the printed shares are about 7 px high in the PDF's bitmap and can be read there on enlargement (9x to 24x); in the bundle crop they are about half that.

## The sample

First and last panel of each figure, bars 1, 8, 15, 22, 29 and 36 from the left: 60 bars. `printed` is the label as read (twice, on enlargements of 9x to 24x of the PDF's bitmap); `measured` is the top of the Correct segment against the y axis (calibrated on the axis ticks, +-0.3); `second` is that measurement repeated on a fresh render of the PDF page at scale 6, with its own calibration and another edge rule. The truth files hold the printed value where there is one (`source: "printed"`) and the measured value, rounded to 0.1, where the print cannot be read (`source: "raster"`, by the coordinator's decision of 2026-11-19); those 36 bars are also listed under `uncertain` there.

| picture | panel | bar | tick label | printed | measured | second | in the truth | nearest k/N |
|---|---|---|---|---|---|---|---|---|
| 10 | 1 `All 2022 ACG questions (N = 300)` | 1 | `GPT-3.5 Web` | `47.7%` | 47.7 |  | 47.7 printed | 143/300 = 47.7 |
| 10 | 1 `All 2022 ACG questions (N = 300)` | 8 | `Claude3-Haiku API` | `50.3%` | 50.4 |  | 50.3 printed | 151/300 = 50.3 |
| 10 | 1 `All 2022 ACG questions (N = 300)` | 15 | `Mistralv2-7b-Q8 Local` | `37.3%` | 37.4 |  | 37.3 printed | 112/300 = 37.3 |
| 10 | 1 `All 2022 ACG questions (N = 300)` | 22 | `Llama2-13b-Q5 Local` | `33.4%` | 33.6 |  | 33.4 printed | 101/300 = 33.7 |
| 10 | 1 `All 2022 ACG questions (N = 300)` | 29 | `Llama3.1-70b Poe` | `58.3%` | 58.5 |  | 58.3 printed | 175/300 = 58.3 |
| 10 | 1 `All 2022 ACG questions (N = 300)` | 36 | `Phi3-3b-Q16 Local` | `42.7%` | 42.7 |  | 42.7 printed | 128/300 = 42.7 |
| 10 | 3 `Question type: image-inclusive (N = 138)` | 1 | `GPT-3.5 Web` | `44.2%` | 44.2 |  | 44.2 printed | 61/138 = 44.2 |
| 10 | 3 `Question type: image-inclusive (N = 138)` | 8 | `Claude3-Haiku API` | `52.9%` | 52.8 |  | 52.9 printed | 73/138 = 52.9 |
| 10 | 3 `Question type: image-inclusive (N = 138)` | 15 | `Mistralv2-7b-Q8 Local` | `37.0%` | 37.0 |  | 37.0 printed | 51/138 = 37.0 |
| 10 | 3 `Question type: image-inclusive (N = 138)` | 22 | `Llama2-13b-Q5 Local` | `30.4%` | 30.6 |  | 30.4 printed | 42/138 = 30.4 |
| 10 | 3 `Question type: image-inclusive (N = 138)` | 29 | `Llama3.1-70b Poe` | `57.2%` | 57.2 |  | 57.2 printed | 79/138 = 57.2 |
| 10 | 3 `Question type: image-inclusive (N = 138)` | 36 | `Phi3-3b-Q16 Local` | `41.3%` | 41.4 |  | 41.3 printed | 57/138 = 41.3 |
| 11 | 1 `Question type: COLON (N = 49)` | 1 | `GPT-3.5 Web` | not legible | 45.0 | 45.0 | 45.0 raster | 22/49 = 44.9 |
| 11 | 1 `Question type: COLON (N = 49)` | 8 | `Claude3-Haiku API` | not legible | 55.0 | 55.0 | 55.0 raster | 27/49 = 55.1 |
| 11 | 1 `Question type: COLON (N = 49)` | 15 | `Mistralv2-7b-Q8 Local` | not legible | 49.2 | 49.2 | 49.2 raster | 24/49 = 49.0 |
| 11 | 1 `Question type: COLON (N = 49)` | 22 | `Llama2-13b-Q5 Local` | not legible | 30.8 | 30.8 | 30.8 raster | 15/49 = 30.6 |
| 11 | 1 `Question type: COLON (N = 49)` | 29 | `Llama3.1-70b Poe` | not legible | 57.1 | 57.1 | 57.1 raster | 28/49 = 57.1 |
| 11 | 1 `Question type: COLON (N = 49)` | 36 | `Phi3-3b-Q16 Local` | not legible | 49.2 | 49.1 | 49.2 raster | 24/49 = 49.0 |
| 11 | 11 `Question type: STOMACH (N = 17)` | 1 | `GPT-3.5 Web` | not legible | 35.5 | 35.5 | 35.5 raster | 6/17 = 35.3 |
| 11 | 11 `Question type: STOMACH (N = 17)` | 8 | `Claude3-Haiku API` | not legible | 41.3 | 41.4 | 41.3 raster | 7/17 = 41.2 |
| 11 | 11 `Question type: STOMACH (N = 17)` | 15 | `Mistralv2-7b-Q8 Local` | not legible | 47.1 | 47.1 | 47.1 raster | 8/17 = 47.1 |
| 11 | 11 `Question type: STOMACH (N = 17)` | 22 | `Llama2-13b-Q5 Local` | not legible | 35.5 | 35.5 | 35.5 raster | 6/17 = 35.3 |
| 11 | 11 `Question type: STOMACH (N = 17)` | 29 | `Llama3.1-70b Poe` | not legible | 47.1 | 47.1 | 47.1 raster | 8/17 = 47.1 |
| 11 | 11 `Question type: STOMACH (N = 17)` | 36 | `Phi3-3b-Q16 Local` | not legible | 47.1 | 47.1 | 47.1 raster | 8/17 = 47.1 |
| 12 | 1 `Question type: Complication (N = 55)` | 1 | `GPT-3.5 Web` | not legible | 56.3 | 56.2 | 56.3 raster | 31/55 = 56.4 |
| 12 | 1 `Question type: Complication (N = 55)` | 8 | `Claude3-Haiku API` | not legible | 52.7 | 52.6 | 52.7 raster | 29/55 = 52.7 |
| 12 | 1 `Question type: Complication (N = 55)` | 15 | `Mistralv2-7b-Q8 Local` | not legible | 34.6 | 34.5 | 34.6 raster | 19/55 = 34.5 |
| 12 | 1 `Question type: Complication (N = 55)` | 22 | `Llama2-13b-Q5 Local` | not legible | 30.8 | 30.7 | 30.8 raster | 17/55 = 30.9 |
| 12 | 1 `Question type: Complication (N = 55)` | 29 | `Llama3.1-70b Poe` | not legible | 58.4 | 58.3 | 58.4 raster | 32/55 = 58.2 |
| 12 | 1 `Question type: Complication (N = 55)` | 36 | `Phi3-3b-Q16 Local` | not legible | 41.7 | 41.6 | 41.7 raster | 23/55 = 41.8 |
| 12 | 5 `Question type: Treatment (N = 217)` | 1 | `GPT-3.5 Web` | not legible | 49.4 | 49.4 | 49.4 raster | 107/217 = 49.3 |
| 12 | 5 `Question type: Treatment (N = 217)` | 8 | `Claude3-Haiku API` | not legible | 51.2 | 51.3 | 51.2 raster | 111/217 = 51.1 |
| 12 | 5 `Question type: Treatment (N = 217)` | 15 | `Mistralv2-7b-Q8 Local` | not legible | 40.2 | 39.9 | 40.2 raster | 87/217 = 40.1 |
| 12 | 5 `Question type: Treatment (N = 217)` | 22 | `Llama2-13b-Q5 Local` | not legible | 33.1 | 33.1 | 33.1 raster | 72/217 = 33.2 |
| 12 | 5 `Question type: Treatment (N = 217)` | 29 | `Llama3.1-70b Poe` | not legible | 57.7 | 57.7 | 57.7 raster | 125/217 = 57.6 |
| 12 | 5 `Question type: Treatment (N = 217)` | 36 | `Phi3-3b-Q16 Local` | not legible | 43.6 | 43.5 | 43.6 raster | 95/217 = 43.8 |
| 13 | 1 `Question Difficulty (Average Human Score): Q1 (N = 75)` | 1 | `GPT-3.5 Web` | not legible | 33.3 | 33.3 | 33.3 raster | 25/75 = 33.3 |
| 13 | 1 `Question Difficulty (Average Human Score): Q1 (N = 75)` | 8 | `Claude3-Haiku API` | not legible | 38.8 | 38.7 | 38.8 raster | 29/75 = 38.7 |
| 13 | 1 `Question Difficulty (Average Human Score): Q1 (N = 75)` | 15 | `Mistralv2-7b-Q8 Local` | not legible | 26.6 | 26.5 | 26.6 raster | 20/75 = 26.7 |
| 13 | 1 `Question Difficulty (Average Human Score): Q1 (N = 75)` | 22 | `Llama2-13b-Q5 Local` | not legible | 23.7 | 24.0 | 23.7 raster | 18/75 = 24.0 |
| 13 | 1 `Question Difficulty (Average Human Score): Q1 (N = 75)` | 29 | `Llama3.1-70b Poe` | not legible | 41.2 | 41.4 | 41.2 raster | 31/75 = 41.3 |
| 13 | 1 `Question Difficulty (Average Human Score): Q1 (N = 75)` | 36 | `Phi3-3b-Q16 Local` | not legible | 29.3 | 29.3 | 29.3 raster | 22/75 = 29.3 |
| 13 | 4 `Question Difficulty (Average Human Score): Q4 (N = 75)` | 1 | `GPT-3.5 Web` | not legible | 56.0 | 56.0 | 56.0 raster | 42/75 = 56.0 |
| 13 | 4 `Question Difficulty (Average Human Score): Q4 (N = 75)` | 8 | `Claude3-Haiku API` | not legible | 56.0 | 56.0 | 56.0 raster | 42/75 = 56.0 |
| 13 | 4 `Question Difficulty (Average Human Score): Q4 (N = 75)` | 15 | `Mistralv2-7b-Q8 Local` | not legible | 44.1 | 44.1 | 44.1 raster | 33/75 = 44.0 |
| 13 | 4 `Question Difficulty (Average Human Score): Q4 (N = 75)` | 22 | `Llama2-13b-Q5 Local` | not legible | 37.6 | 37.8 | 37.6 raster | 28/75 = 37.3 |
| 13 | 4 `Question Difficulty (Average Human Score): Q4 (N = 75)` | 29 | `Llama3.1-70b Poe` | not legible | 73.3 | 73.4 | 73.3 raster | 55/75 = 73.3 |
| 13 | 4 `Question Difficulty (Average Human Score): Q4 (N = 75)` | 36 | `Phi3-3b-Q16 Local` | not legible | 46.8 | 46.8 | 46.8 raster | 35/75 = 46.7 |
| 14 | 1 `Question type: Long (N = 99)` | 1 | `GPT-3.5 Web` | `42.4%` | 42.4 |  | 42.4 printed | 42/99 = 42.4 |
| 14 | 1 `Question type: Long (N = 99)` | 8 | `Claude3-Haiku API` | `50.5%` | 50.6 |  | 50.5 printed | 50/99 = 50.5 |
| 14 | 1 `Question type: Long (N = 99)` | 15 | `Mistralv2-7b-Q8 Local` | `38.4%` | 38.3 |  | 38.4 printed | 38/99 = 38.4 |
| 14 | 1 `Question type: Long (N = 99)` | 22 | `Llama2-13b-Q5 Local` | `33.3%` | 33.1 |  | 33.3 printed | 33/99 = 33.3 |
| 14 | 1 `Question type: Long (N = 99)` | 29 | `Llama3.1-70b Poe` | `55.6%` | 55.5 |  | 55.6 printed | 55/99 = 55.6 |
| 14 | 1 `Question type: Long (N = 99)` | 36 | `Phi3-3b-Q16 Local` | `42.4%` | 42.4 |  | 42.4 printed | 42/99 = 42.4 |
| 14 | 3 `Question type: Short (N = 102)` | 1 | `GPT-3.5 Web` | `49.0%` | 49.1 |  | 49.0 printed | 50/102 = 49.0 |
| 14 | 3 `Question type: Short (N = 102)` | 8 | `Claude3-Haiku API` | `48.0%` | 48.0 |  | 48.0 printed | 49/102 = 48.0 |
| 14 | 3 `Question type: Short (N = 102)` | 15 | `Mistralv2-7b-Q8 Local` | `38.2%` | 38.2 |  | 38.2 printed | 39/102 = 38.2 |
| 14 | 3 `Question type: Short (N = 102)` | 22 | `Llama2-13b-Q5 Local` | `38.6%` | 38.6 |  | 38.6 printed | 39/102 = 38.2 |
| 14 | 3 `Question type: Short (N = 102)` | 29 | `Llama3.1-70b Poe` | `52.9%` | 53.1 |  | 52.9 printed | 54/102 = 52.9 |
| 14 | 3 `Question type: Short (N = 102)` | 36 | `Phi3-3b-Q16 Local` | `43.1%` | 43.2 |  | 43.1 printed | 44/102 = 43.1 |

The two measurements of the 36 unreadable bars differ by 0.28 at most; none moved by more than 0.5. The largest difference is `Mistralv2-7b-Q8 Local` in the Treatment panel of picture 12, whose Correct segment ends against the gridline of 40. The edge rule of the second measurement was corrected twice before this comparison: its first versions stopped at stacked label boxes or took a thin 2OP segment over the green for part of it on a few bars; close-ups of those bars showed the fault was in that rule and the first values stood.

24 of the 60 printed shares could be read (pictures 10 and 14); they differ from the measured bar tops by 0.19 at most. Two of them are not multiples of 1/N of their panel: `Llama2-13b-Q5 Local` prints 33.4% in the panel of all 300 questions (100/299) and 38.6% in the Short panel (39/101), so this model has one question less than the panel title says, and the last column is not a safe way to fill in a share that cannot be read.

