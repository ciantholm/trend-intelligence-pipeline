# Trend Intelligence Pipeline
### Issue 001 — Black-Owned Fashion & Beauty Brands

A small, real AI engineering pipeline: it takes raw search-traffic data, computes
trend metrics in plain Python (no AI, so the numbers can't be hallucinated), then
sends *only those computed metrics* to Claude to interpret — direction, confidence,
and a clearly-labeled hypothesis for why. Output is a single markdown report.

This is the repeatable version of the manual research you did in chat: same
brands, same real Semrush data, but running as a script instead of you asking
me questions one at a time.

## What's in this folder

```
trend-pipeline/
├── data/
│   └── brand_traffic.csv       # seed dataset: 11 brands, monthly organic traffic, Nov 2025-Jun 2026
├── trend_pipeline.py           # the pipeline itself
├── output/
│   └── trend_report.md         # generated when you run the script
└── README.md
```

## Setup

```bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

Get a key at console.anthropic.com if you don't have one yet.

## Run it

```bash
python trend_pipeline.py
```

You'll see progress printed per brand, then a full report written to
`output/trend_report.md`.

## How the pipeline is structured (and why it counts as "AI engineering")

1. **`load_traffic_data()`** — reads the CSV, groups by brand, sorts chronologically.
   Pure data handling, no AI.
2. **`compute_metrics()`** — calculates % change, peak month, and a spike detector
   (any month-over-month move ≥40%). Still no AI — this is the part that has to be
   trustworthy, so it's just math.
3. **`analyze_brand()`** — the only step that touches Claude. It sends the
   *computed* metrics (not raw opinions, not the CSV) and constrains the response
   to a strict JSON schema: trend direction, confidence, headline, a hypothesis
   labeled as a hypothesis, and what to check next run.
4. **`build_report()`** — assembles everything into one markdown file.

Splitting it this way is the actual engineering decision worth explaining in your
portfolio case study: the AI never sees raw numbers it could restate wrong, and it
never gets to invent a narrative without labeling it as speculation.

## Making it fully live

Right now `load_traffic_data()` reads the seed CSV pulled from Semrush's
`resource_rank_history` report during research. To automate data collection too,
swap that function for a live call to Semrush's API (needs your own Semrush API
key), shaped into the same per-row structure. Nothing else in the pipeline has
to change — that's the point of keeping data-loading separate from analysis.

## Extending it

- Add more brands: just append rows to `brand_traffic.csv` in the same format.
- Add more months: same, one row per brand per month.
- Change the AI's focus: edit `SYSTEM_PROMPT` in `trend_pipeline.py` — e.g. ask
  it to flag brands worth a retail partnership pitch, or brands showing early
  decline before it's public news (see: Ami Colé in the seed data).
