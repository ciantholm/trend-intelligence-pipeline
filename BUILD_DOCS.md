# Trend Intelligence Pipeline. Build Docs

Repo: github.com/ciantholm/trend-intelligence-pipeline
Written retroactively, after the build, as documentation of intent and architecture. Useful as a portfolio artifact and as a template for the next project.

---

## BI. Build Intent

**Origin**
This didn't start as a build-a-portfolio-project exercise. It started with a school impact analysis on FUBU: a brand that went from over $6 billion in total retail sales to withdrawing from the U.S. market by 2003, largely from overbuying and failing to evolve. That paper raised a real question that couldn't be answered with qualitative research alone. As FUBU eyes a comeback, is renewed interest actually backed by demand, or is it just nostalgia and press cycles? Answering that meant pulling real traffic and search data, not just reading articles about the brand's history. That's what the pipeline was built to do.

**Goals**
Turn the FUBU question into a repeatable method: take a brand's comeback or collapse narrative and test it against real search and traffic data instead of taking the narrative at face value. Prove the method holds up across more than one brand, so it's a tool, not a one-off argument.

**Success metrics**
- Pipeline runs end to end on real Semrush data for a batch of brands, not one demo case.
- Output includes a number and a direction, not just a description. Example: Baby Phat +89.4% sustained, FUBU -91.5% hype-to-collapse, matching the overbuying/no-evolution story from the impact analysis with actual data.
- At least one finding predicts or explains a real-world outcome (Ami Colé's traffic decline visible before its public closure).
- Deliverable is publishable as a standalone case study, not just a script in a folder.

**User personas**
- Primary: hiring managers and recruiters screening for analytical and AI-fluency skill, specifically in ecommerce ops, content strategy, or instructional design roles.
- Secondary: Angel herself, using the pipeline as a repeatable tool for future brand research (Brand Desk clients, day trading research, or her own trend content).

---

## BAP. Build Applications

**Hi-fi mockups**
No formal mockup phase. The output format (a single markdown report) was defined directly through the JSON schema built into `analyze_brand()`, which locks the AI's response into trend direction, confidence, headline, and a labeled hypothesis before `build_report()` assembles it into the final file.

**User flows**
1. Input: brand rows in `brand_traffic.csv` (monthly organic traffic per brand).
2. `load_traffic_data()` reads and sorts the CSV. No AI involved.
3. `compute_metrics()` calculates % change, peak month, and spike detection. Still no AI, just math, so the numbers can't be hallucinated.
4. `analyze_brand()` sends only the computed metrics to Claude, constrained to a strict JSON schema.
5. `build_report()` assembles everything into `output/trend_report.md`.

**Customer interface**
Command line script. Run `python trend_pipeline.py`, watch per-brand progress print, then read the generated report. No web UI or notebook. Re-running for a new brand means adding a row to the CSV and running the script again.

---

## BIM. Build Implementation

**System architecture**
- Language: Python
- Data source: `brand_traffic.csv` (seed dataset, 11 brands, monthly organic traffic pulled from Semrush's `resource_rank_history` report)
- Analysis layer: Anthropic API (Claude), fed only computed metrics, returns structured JSON
- Output: single markdown report (`output/trend_report.md`), later adapted into a case study writeup and LinkedIn carousel (v3, corrected)
- Orchestration: single entry point (`trend_pipeline.py`), run manually per batch. No scheduling or automation yet.

**Data flows**
CSV (raw monthly traffic) → `load_traffic_data()` → `compute_metrics()` (% change, peak month, spike detection) → `analyze_brand()` (Claude, JSON-constrained) → `build_report()` → markdown report.
Data lives in a flat CSV between steps, no database. Deliberately simple so the pipeline stays inspectable end to end.

**Tech spec choices**
- Semrush over other tools: existing access through school/work tools, and traffic history depth was sufficient to show trend direction over an 8-month window without needing a paid dedicated trend API.
- Splitting math from AI: `compute_metrics()` does all the arithmetic in plain Python before anything touches Claude. This is the core engineering decision. The model never sees raw numbers it could restate wrong, and it's never in a position to invent a trend that isn't backed by the computed data.
- JSON structured output: forces the model to label its hypothesis as a hypothesis rather than asserting it as fact, and makes the output directly reusable in `build_report()` without parsing free text.
- CSV over a database: the dataset is small (11 brands, monthly) and the priority was making the pipeline easy to extend by hand (add a row) rather than building infrastructure the project didn't need yet.

---

**11 brands analyzed.** The first report named 3 headline cases (Baby Phat, FUBU, Ami Colé). Running the full seed dataset confirms the pattern holds across the batch: Baby Phat +89.4% (strongest sustained comeback), Karl Kani +5.0% and Brother Vellies +1.8% (flat), Cross Colours -1.5% (flat), Telfar -24.8% (notable pullback), Rocawear -43.6% and Phat Farm -45.2% (clear decline), FUBU -91.5% (hype vs. demand cautionary tale), Sean John -95.7% (near-total collapse), Ami Colé -99.5% (traffic collapse visible ahead of public closure), Freddie Estelle -100.0% (traffic went to zero). See `graph.png` for the full comparison.
