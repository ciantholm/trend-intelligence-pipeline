"""
Trend Intelligence Pipeline — Black-Owned Fashion & Beauty Brands
Issue 001 of the Trend Intelligence project.

WHAT THIS DOES
--------------
1. Loads monthly organic-search traffic data per brand (data/brand_traffic.csv).
2. Computes trend metrics for each brand: % change, spike detection, trajectory.
3. Sends each brand's metrics + raw history to Claude, which returns a structured
   JSON verdict: trend direction, confidence, and a plain-English "why" grounded
   only in the numbers (no invented narrative).
4. Assembles everything into a single markdown trend report.

HOW TO RUN
----------
1. pip install anthropic pandas
2. Set your API key:  export ANTHROPIC_API_KEY="sk-ant-..."
3. python trend_pipeline.py

DATA SOURCE
-----------
The seed CSV in data/brand_traffic.csv was pulled from Semrush's
resource_rank_history report (organic traffic, Nov 2025 - Jun 2026).
To make this fully live, swap load_traffic_data() for a real Semrush API call
(see the SEMRUSH_API_NOTE at the bottom of this file).
"""

import os
import json
import csv
from collections import defaultdict
from datetime import datetime

import anthropic

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "brand_traffic.csv")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output", "trend_report.md")
MODEL = "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------------------------

def load_traffic_data(csv_path=CSV_PATH):
    """Reads the CSV and groups monthly rows by brand, sorted chronologically."""
    by_brand = defaultdict(list)
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            row["organic_traffic"] = int(row["organic_traffic"])
            row["organic_keywords"] = int(row["organic_keywords"])
            row["semrush_rank"] = int(row["semrush_rank"])
            row["date"] = datetime.strptime(row["date"], "%Y-%m-%d")
            by_brand[row["brand"]].append(row)
    for brand in by_brand:
        by_brand[brand].sort(key=lambda r: r["date"])
    return by_brand


# ---------------------------------------------------------------------------
# 2. COMPUTE TREND METRICS (pure math, no AI — keeps the AI step honest)
# ---------------------------------------------------------------------------

def compute_metrics(history):
    """Given a chronological list of monthly rows for one brand, return
    summary stats the AI step will be constrained to reason from."""
    first, last = history[0], history[-1]
    traffic_series = [r["organic_traffic"] for r in history]
    peak = max(traffic_series)
    peak_month = history[traffic_series.index(peak)]["date"].strftime("%Y-%m")

    pct_change = (
        round((last["organic_traffic"] - first["organic_traffic"]) / first["organic_traffic"] * 100, 1)
        if first["organic_traffic"] > 0 else None
    )

    # Simple spike detector: any month-over-month jump/drop over 40%
    spikes = []
    for prev, curr in zip(history, history[1:]):
        if prev["organic_traffic"] > 0:
            mom_change = (curr["organic_traffic"] - prev["organic_traffic"]) / prev["organic_traffic"] * 100
            if abs(mom_change) >= 40:
                spikes.append({
                    "month": curr["date"].strftime("%Y-%m"),
                    "change_pct": round(mom_change, 1)
                })

    return {
        "brand": first["brand"],
        "domain": first["domain"],
        "category": first["category"],
        "start_month": first["date"].strftime("%Y-%m"),
        "end_month": last["date"].strftime("%Y-%m"),
        "start_traffic": first["organic_traffic"],
        "end_traffic": last["organic_traffic"],
        "pct_change_over_period": pct_change,
        "peak_traffic": peak,
        "peak_month": peak_month,
        "spikes": spikes,
        "monthly_series": [
            {"month": r["date"].strftime("%Y-%m"), "traffic": r["organic_traffic"]}
            for r in history
        ],
    }


# ---------------------------------------------------------------------------
# 3. AI STEP — Claude reasons over the metrics, not the other way around
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a trend analyst for a fashion/beauty intelligence pipeline.
You will be given computed search-traffic metrics for one brand — real numbers,
already calculated. Your job is to interpret them, not invent additional facts.

Respond with ONLY a JSON object, no preamble, no markdown fences, in this exact shape:
{
  "trend_direction": "rising" | "declining" | "flat" | "volatile",
  "confidence": "high" | "medium" | "low",
  "headline": "<one sentence, plain English, grounded only in the numbers>",
  "likely_driver": "<one sentence hypothesis for WHY, clearly framed as a hypothesis, not a fact>",
  "watch_next": "<one sentence: what a follow-up run of this pipeline should check>"
}

Rules:
- Never state a cause as fact unless it's implied directly by spike timing.
- If data is too thin or erratic to say anything meaningful, say so at low confidence.
- Keep every field under 30 words.
"""


def analyze_brand(client, metrics):
    user_content = json.dumps(metrics, indent=2)
    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    raw = response.content[0].text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "trend_direction": "unknown",
            "confidence": "low",
            "headline": "Model did not return valid JSON — see raw output.",
            "likely_driver": raw[:200],
            "watch_next": "Re-run this brand; check prompt/response formatting.",
        }


# ---------------------------------------------------------------------------
# 4. REPORT ASSEMBLY
# ---------------------------------------------------------------------------

def build_report(results):
    lines = [
        "# Trend Intelligence Report — Black-Owned Fashion & Beauty Brands",
        f"_Generated {datetime.now().strftime('%B %d, %Y')} · {len(results)} brands analyzed_",
        "",
        "## Summary Table",
        "",
        "| Brand | Trend | Confidence | Change (period) |",
        "|---|---|---|---|",
    ]
    for r in results:
        m, a = r["metrics"], r["analysis"]
        pct = f"{m['pct_change_over_period']}%" if m["pct_change_over_period"] is not None else "n/a"
        lines.append(f"| {m['brand']} | {a['trend_direction']} | {a['confidence']} | {pct} |")

    lines.append("")
    lines.append("## Brand Detail")
    for r in results:
        m, a = r["metrics"], r["analysis"]
        lines.append(f"\n### {m['brand']}")
        lines.append(f"**{a['headline']}**")
        lines.append(f"- Likely driver (hypothesis): {a['likely_driver']}")
        lines.append(f"- Watch next: {a['watch_next']}")
        if m["spikes"]:
            spike_str = ", ".join(f"{s['month']} ({s['change_pct']:+.1f}%)" for s in m["spikes"])
            lines.append(f"- Notable month-over-month spikes: {spike_str}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "Set ANTHROPIC_API_KEY before running.\n"
            "  export ANTHROPIC_API_KEY='sk-ant-...'"
        )

    client = anthropic.Anthropic(api_key=api_key)
    by_brand = load_traffic_data()

    results = []
    for brand, history in by_brand.items():
        metrics = compute_metrics(history)
        analysis = analyze_brand(client, metrics)
        results.append({"metrics": metrics, "analysis": analysis})
        print(f"Analyzed: {brand} -> {analysis['trend_direction']} ({analysis['confidence']})")

    report = build_report(results)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(report)
    print(f"\nReport written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# SEMRUSH_API_NOTE
# ---------------------------------------------------------------------------
# To pull live data instead of the seed CSV, replace load_traffic_data() with
# a call to Semrush's Analytics API (resource_rank_history / domain_rank_history
# endpoint), authenticated with your own Semrush API key. Shape the response
# into the same list-of-dicts-per-brand structure this file expects
# (brand, domain, category, date, organic_traffic, organic_keywords, semrush_rank)
# and everything downstream (compute_metrics, analyze_brand, build_report)
# works unchanged. That's the whole point of separating these steps.
