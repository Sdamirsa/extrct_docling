# Figure 6, read again after the fix

In the four runs of the round every reader was given Figure 6 (S05,
`#/pictures/5`) with black where the page is white: the figure is one image
with a transparency mask, and the prepare phase took the image's pixels
without it ([`../LOG.md`](../LOG.md), section 7). The axis titles and tick
labels, printed in black on that part, were gone.

After the fix the figure was prepared again from the first run's bundle,
outside the bundles, and each method read it once more:

```bash
amir-figdata prepare samples/round-4-showcase/cloud-sonnet-5-5/Public-test-manuscript \
    --pdf-dir showcase --refs '#/pictures/5' --out <work>/prepared
# one copy of <work>/prepared per label, then
amir-figdata read <work>/<label> --method <method> [--model google/gemini-3.8-flash]
```

| | first pass: values under the right name | after the fix | seconds | cost USD |
|---|---|---|---|---|
| `ollama`, Gemma 4 26B | 0 of 13 | 13 of 13 | 44 | local |
| `cloud`, Sonnet 5.5 | 0 of 13 | 13 of 13 | 13 | 0.03 |
| `cloud`, Gemini 3.8 Flash | 0 of 13 | 13 of 13 | 146 | 0.12 |
| `agent`, Sonnet 5.5 | 0 of 13 | 13 of 13 | 22 | 0.07 |

13 of the truth's 17 rows have a value. In the first pass every run
returned the 13 printed numbers; none could say at which year or date a
point stands. [`S05.json`](S05.json) has both passes per run; `runs/` the
readings and run records of the second.

The four bundles of the round hold the figure as first read.
