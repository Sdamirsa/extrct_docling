# One paper, the whole pipeline, each method

Paper: `showcase/Public-test-manuscript.pdf`. Written by `scripts/compare_bundles.py`.

## Time and cost of one `amir-batch` command

| run | command s | conversion s | reading s | rest s | cost USD | calls | output tokens |
|---|---|---|---|---|---|---|---|
| ollama-gemma4-26b-qat | 2355 | 696 | 1609 | 50 | local | 51 | 58061 |
| cloud-sonnet-5-5 | 1093 | 683 | 358 | 52 | 0.91 | 12 | 70622 |
| cloud-gemini-3-8-flash | 2532 | 673 | 1809 | 51 | 1.42 | 12 | 352833 |
| agent-sonnet-5-5 | 1614 | 707 | 854 | 53 | 2.97 | 12 | 144494 |

## What the step made of the chart candidates

| run | read | no data | not read | failed | charts | values |
|---|---|---|---|---|---|---|
| ollama-gemma4-26b-qat | 10 | 0 | 2 | 0 | 39 | 1061 |
| cloud-sonnet-5-5 | 10 | 1 | 1 | 0 | 35 | 867 |
| cloud-gemini-3-8-flash | 11 | 1 | 0 | 0 | 39 | 1529 |
| agent-sonnet-5-5 | 11 | 1 | 0 | 0 | 40 | 1970 |

## What reached the bundle

| run | table at the figure | pointer only | chunks | chunks with figure data | markdown bytes | check |
|---|---|---|---|---|---|---|
| ollama-gemma4-26b-qat | 7 | 3 | 164 | 10 | 231118 | ok |
| cloud-sonnet-5-5 | 9 | 1 | 171 | 10 | 240654 | ok |
| cloud-gemini-3-8-flash | 11 | 0 | 189 | 11 | 269945 | ok |
| agent-sonnet-5-5 | 9 | 2 | 172 | 11 | 245691 | ok |

## Against the truth (6 figures, 573 values)

Three counts of values within 5 % of the axis range. *As scored*: the bench's scorer of the earlier rounds, which pairs charts by the overlap of their boxes and values by names less than a fifth apart, first fit. *By name*: a chart whose box pairs with none is merged into the truth chart that holds it, or paired by its id or its place (a chart cut in two, or charts without a box, still count), and a value is paired with the value under the same printed name. *Names ignored*: with the charts placed the same way, the sorted values of paired charts are compared, whatever they are called; an upper bound that lets chance matches through.

| run | returned | as scored | by name | names ignored | by name, with the figure read again after the fix |
|---|---|---|---|---|---|
| ollama-gemma4-26b-qat | 344 | 67 | 83 | 190 | 96 |
| cloud-sonnet-5-5 | 431 | 331 | 408 | 421 | 421 |
| cloud-gemini-3-8-flash | 573 | 526 | 554 | 568 | 567 |
| agent-sonnet-5-5 | 268 | 213 | 251 | 264 | 264 |

## The judges (the figures with a truth file)

| run | correct | partial | wrong | missed | usable | would mislead | dominant failure |
|---|---|---|---|---|---|---|---|
| ollama-gemma4-26b-qat | 0 | 6 | 0 | 0 | 0 of 6 | 3 | GEOMETRY_MISMEASURED |
| cloud-sonnet-5-5 | 4 | 2 | 0 | 0 | 5 of 6 | 0 | MISSING_VALUES |
| cloud-gemini-3-8-flash | 4 | 2 | 0 | 0 | 4 of 6 | 0 | VALUE_ASSIGNMENT |
| agent-sonnet-5-5 | 3 | 3 | 0 | 0 | 5 of 6 | 0 | MISSING_VALUES |

| figure | ollama-gemma4-26b-qat | cloud-sonnet-5-5 | cloud-gemini-3-8-flash | agent-sonnet-5-5 |
|---|---|---|---|---|
| S02 | partial, severity 3, not usable | partial, severity 2 | correct, severity 1 | correct, severity 1 |
| S03 | partial, severity 3, not usable | partial, severity 2 | partial, severity 2, not usable | partial, severity 2 |
| S04 | partial, severity 3, not usable | correct, severity 1 | partial, severity 2, not usable | partial, severity 2 |
| S05 | partial, severity 2, not usable | correct, severity 0, not usable | correct, severity 1 | partial, severity 2, not usable |
| S06 | partial, severity 2, not usable | correct, severity 1 | correct, severity 1 | correct, severity 1 |
| S08 | partial, severity 2, not usable | correct, severity 1 | correct, severity 0 | correct, severity 0 |

## Against the sampled bars (5 dense figures, 60 values)

A sample fixed by rule: in the first and the last panel of each figure, the share of Correct of bars 1, 8, 15, 22, 29 and 36 (printed where the print can be read, else measured against the axis).

| run | sampled bars returned under the bar's name | within 5 % |
|---|---|---|
| ollama-gemma4-26b-qat | 22 | 8 |
| cloud-sonnet-5-5 | 38 | 38 |
| cloud-gemini-3-8-flash | 60 | 55 |
| agent-sonnet-5-5 | 60 | 60 |

## Per figure: status, values returned (within 5 % of the truth by name, or of the sampled bars)

| figure | truth | ollama-gemma4-26b-qat | cloud-sonnet-5-5 | cloud-gemini-3-8-flash | agent-sonnet-5-5 |
|---|---|---|---|---|---|
| S02 | 75 | read, 75 (23) | read, 75 (69) | read, 75 (75) | read, 75 (75) |
| S03 | 222 | read, 54 (10) | read, 80 (80) | read, 222 (222) | read, 37 (37) |
| S04 | 144 | read, 64 (24) | read, 144 (144) | read, 144 (142) | read, 24 (24) |
| S05 | 17 | read, 17 (0; read again after the fix: 13) | read, 17 (0; read again after the fix: 13) | read, 17 (0; read again after the fix: 13) | read, 17 (0; read again after the fix: 13) |
| S06 | 52 | read, 107 (26) | read, 52 (52) | read, 52 (52) | read, 52 (52) |
| S08 | 63 | read, 27 (0) | read, 63 (63) | read, 63 (63) | read, 63 (63) |
| S09 | none | not_read, 0 | no_data, 0 | no_data, 0 | no_data, 0 |
| S10 | sample of 12 | read, 122 (2) | read, 111 (12) | read, 111 (12) | read, 111 (12) |
| S11 | sample of 12 | read, 181 (1) | read, 66 (2) | read, 396 (9) | read, 407 (12) |
| S12 | sample of 12 | not_read, 0 (0) | not_read, 0 (0) | read, 190 (11) | read, 185 (12) |
| S13 | sample of 12 | read, 302 (2) | read, 148 (12) | read, 148 (12) | read, 888 (12) |
| S14 | sample of 12 | read, 112 (3) | read, 111 (12) | read, 111 (11) | read, 111 (12) |

## Agreement between runs

The share of the row run's values that the column run has within 5 % of the axis range under the same chart, category and series, summed over the figures both were given. It needs no truth, and it is not accuracy: two runs can agree on a wrong value.

| | ollama-gemma4-26b-qat | cloud-sonnet-5-5 | cloud-gemini-3-8-flash | agent-sonnet-5-5 |
|---|---|---|---|---|
| ollama-gemma4-26b-qat |  | 0.14 | 0.13 | 0.14 |
| cloud-sonnet-5-5 | 0.16 |  | 0.94 | 0.80 |
| cloud-gemini-3-8-flash | 0.09 | 0.53 |  | 0.70 |
| agent-sonnet-5-5 | 0.09 | 0.35 | 0.54 |  |
