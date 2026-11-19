# One paper, the whole pipeline, each method

Paper: `showcase/Public-test-manuscript.pdf`. Written by `scripts/compare_bundles.py`.

## Time and cost of one `amir-batch` command

| run | command s | conversion s | reading s | rest s | cost USD | calls | output tokens |
|---|---|---|---|---|---|---|---|
| ollama-gemma4-26b-qat | 2694 | 610 | 2024 | 60 | local | 48 | 67686 |
| cloud-sonnet-5-5 | 1091 | 610 | 94 | 387 | 0.23 | 4 | 16072 |

## What the step made of the chart candidates

| run | read | no data | not read | failed | charts | values |
|---|---|---|---|---|---|---|
| ollama-gemma4-26b-qat | 11 | 0 | 1 | 0 | 37 | 1523 |
| cloud-sonnet-5-5 | 2 | 0 | 0 | 0 | 15 | 161 |

## What reached the bundle

| run | table at the figure | pointer only | chunks | chunks with figure data | markdown bytes | check |
|---|---|---|---|---|---|---|
| ollama-gemma4-26b-qat | 8 | 3 | 165 | 11 | 232558 | ok |
| cloud-sonnet-5-5 | 9 | 2 | 169 | 11 | 238928 | ok |

## Against the truth (6 figures, 573 values)

Three counts of values within 5 % of the axis range. *As scored*: the bench's scorer of the earlier rounds, which pairs charts by the overlap of their boxes and values by names less than a fifth apart, first fit. *By name*: a chart whose box pairs with none is merged into the truth chart that holds it, or paired by its id or its place (a chart cut in two, or charts without a box, still count), and a value is paired with the value under the same printed name. *Names ignored*: with the charts placed the same way, the sorted values of paired charts are compared, whatever they are called; an upper bound that lets chance matches through.

| run | returned | as scored | by name | names ignored | by name, with the figure read again after the fix |
|---|---|---|---|---|---|
| ollama-gemma4-26b-qat | 361 | 137 | 148 | 183 | 148 |
| cloud-sonnet-5-5 | 0 | 366 | 378 | 378 | 378 |

## Against the sampled bars (5 dense figures, 60 values)

A sample fixed by rule: in the first and the last panel of each figure, the share of Correct of bars 1, 8, 15, 22, 29 and 36 (printed where the print can be read, else measured against the axis).

| run | sampled bars returned under the bar's name | within 5 % |
|---|---|---|
| ollama-gemma4-26b-qat | 31 | 9 |
| cloud-sonnet-5-5 | 46 | 46 |

## Per figure: status, values returned (within 5 % of the truth by name, or of the sampled bars)

| figure | truth | ollama-gemma4-26b-qat | cloud-sonnet-5-5 |
|---|---|---|---|
| S02 | 75 | read, 75 (23) | not prepared, 0 (69) |
| S03 | 222 | read, 74 (37) | not prepared, 0 (37) |
| S04 | 144 | read, 64 (24) | not prepared, 0 (144) |
| S05 | 17 | read, 17 (13) | not prepared, 0 (13) |
| S06 | 52 | read, 104 (51) | not prepared, 0 (52) |
| S08 | 63 | read, 27 (0) | not prepared, 0 (63) |
| S09 | none | not_read, 0 | not prepared, 0 |
| S10 | sample of 12 | read, 122 (2) | not prepared, 0 (12) |
| S11 | sample of 12 | read, 183 (0) | read, 13 (2) |
| S12 | sample of 12 | read, 297 (0) | not prepared, 0 (8) |
| S13 | sample of 12 | read, 302 (2) | read, 148 (12) |
| S14 | sample of 12 | read, 258 (5) | not prepared, 0 (12) |

## Agreement between runs

The share of the row run's values that the column run has within 5 % of the axis range under the same chart, category and series, summed over the figures both were given. It needs no truth, and it is not accuracy: two runs can agree on a wrong value.

| | ollama-gemma4-26b-qat | cloud-sonnet-5-5 |
|---|---|---|
| ollama-gemma4-26b-qat |  | 0.13 |
| cloud-sonnet-5-5 | 0.12 |  |
