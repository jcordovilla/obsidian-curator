# Obsidian Curator — Implementation Guide (Improvements 1, 2, 3, 6, 7, 8, 9, 10, 11, 12)

> **Scope**: This document gives **precise, implementation‑ready** steps for 10 improvements to Obsidian Curator.  
> It intentionally **omits** Improvements **#4 (Related Notes & MOCs)** and **#5 (Incremental/Resumable Runs)** as requested.

---

## Conventions & Assumptions

- **Repo layout** (from current docs):  
  `obsidian_curator/` → `core.py`, `models.py`, `content_processor.py`, `ai_analyzer.py`, `theme_classifier.py`, `vault_organizer.py`, `cli.py`  
  `docs/`, `tests/`, `examples/`, `metadata/` (runtime output)  
- **Python**: 3.12+, **Poetry** used for deps.  
- **Logging**: `loguru` already present.  
- **Config**: YAML via `PyYAML`; Pydantic models in `models.py`.
- **AI**: Local via Ollama, small/medium/large models available.
- **Feature flags**: Each improvement adds a config key; default to **off** if risky or **on** if safe.

---

## Table of Contents

1. [Borderline Triage Loop (Human‑in‑the‑Loop)](#1-borderline-triage-loop-human-in-the-loop)  
2. [Score Calibration via Tiny Gold Set](#2-score-calibration-via-tiny-gold-set)  
3. [Duplicate & Near‑Duplicate Clustering](#3-duplicate--near-duplicate-clustering)  
6. [Model Routing Cascade with Escalation](#6-model-routing-cascade-with-escalation)  
7. [Content‑Type Specific Rules](#7-content-type-specific-rules)  
8. [Unicode & Boilerplate Sanitation Pass](#8-unicode--boilerplate-sanitation-pass)  
9. [Writer‑Facing Artifacts: Briefs & Stubs](#9-writer-facing-artifacts-briefs--stubs)  
10. [Evaluation Harness & Regression Tests](#10-evaluation-harness--regression-tests)  
11. [Provenance, Licensing & Citation Hygiene](#11-provenance-licensing--citation-hygiene)  
12. [Observability: Rich Metrics & Traces](#12-observability-rich-metrics--traces)

---

## 1) Borderline Triage Loop (Human‑in‑the‑Loop)

### Goal
Protect precision without losing recall: notes within a small **gray‑zone** around thresholds go to a **Triage** queue for one‑click Keep/Discard.

### Config (`config.yaml`)
```yaml
triage:
  enabled: true
  margin: 0.05                 # gray‑zone window around thresholds
  dimensions: ["overall", "relevance", "professional_writing"]
  persist_path: "metadata/triage.jsonl"
  auto_escalate_model: "llama3.1:8b"  # optional: re‑score borderline with this model
```

### Data Models (`models.py`)
```python
from pydantic import BaseModel
from typing import Optional, Dict

class TriageItem(BaseModel):
    note_path: str
    scores: Dict[str, float]    # e.g., {"overall": 0.66, "relevance": 0.64, ...}
    thresholds: Dict[str, float]
    decision_suggested: str     # "keep" | "discard"
    reason: str
    escalated_model: Optional[str] = None
    user_decision: Optional[str] = None  # "keep" | "discard"
    decided_at: Optional[str] = None     # ISO timestamp
```

### Logic (`core.py` → within curation loop)
- After `AIAnalyzer`, compute `abs(score - threshold)` for configured dimensions.
- If any is ≤ `triage.margin` → create `TriageItem` and **skip final decision** until resolved.
- Optional: re‑score with `auto_escalate_model` before pushing to triage.

### GUI/CLI
- **GUI**: Add **Triage** tab → table with note preview and **Keep/Discard** buttons; persist `user_decision` to `triage.jsonl`.
- **CLI**: `--triage-review` opens an interactive prompt over borderline notes (arrow keys + K/D).

### Acceptance
- Gray‑zone notes are withheld from final placement until decided.
- Decisions persist; re‑runs never ask again for the same fingerprint (if you implement fingerprints later).
- Target: +10–15% useful content with <5% noise growth on a sampled evaluation (see §10).

---

## 2) Score Calibration via Tiny Gold Set

### Goal
Learn **your** actual bar using a one‑time labeled set (150–300 notes) and transform raw LLM scores into a calibrated **keep probability** per content type.

### Config (`config.yaml`)
```yaml
calibration:
  enabled: true
  goldset_path: "metadata/goldset.jsonl"     # [{"note_path":..., "label": "keep"|"discard"}]
  model_path: "metadata/calibration.json"    # learned parameters
  per_type: true                             # learn per content_type (PERSONAL_NOTE, WEB_CLIPPING...)
  features:
    - "scores.overall"
    - "scores.relevance"
    - "scores.professional_writing"
    - "scores.analytical_depth"
    - "meta.length_chars"
    - "meta.content_type"
```

### Data Models (`models.py`)
```python
class CalibrationConfig(BaseModel):
    enabled: bool = False
    goldset_path: str
    model_path: str
    per_type: bool = True
    features: list[str]
```

### Implementation
- Add `calibration.py`:
  - Load gold set; extract features from stored `CurationResult`.
  - Fit **logistic regression** (pure‑python fallback or `scikit‑learn` if allowed).
  - Persist coefficients per content type.
- In `core.py` post‑analysis, compute calibrated `keep_prob` and compare to `keep_prob_threshold` (derive from existing thresholds).

### CLI
- `obsidian-curator calibrate --goldset metadata/goldset.jsonl`
- `obsidian-curator curate --use-calibration`

### Acceptance
- Report **AUC/F1** uplift vs. raw thresholds on a holdout split.
- Persisted calibration is applied automatically in subsequent runs.

---

## 3) Duplicate & Near‑Duplicate Clustering

### Goal
Remove exact and near‑duplicates; keep the **canonical** best version and link alternates in frontmatter.

### Config (`config.yaml`)
```yaml
dedupe:
  enabled: true
  exact: true
  near:
    method: "minhash"     # options: "minhash" | "simhash" | "difflib"
    threshold: 0.90       # similarity cut; tune per method
  write_aliases: true
  report_path: "metadata/duplicates.md"
```

### Implementation
- **Exact**: normalized text → SHA‑256; drop repeats.
- **Near**: choose one method:
  - **MinHash/Jaccard** on 5‑word shingles (via `datasketch`) or
  - **SimHash** (via `py-simhash`) or
  - **difflib.SequenceMatcher** fallback (no extra deps).
- Select **canonical** by higher `overall` then `professional_writing` then most recent `modified_at`.
- Write other members under frontmatter key:
  ```yaml
  duplicates:
    - path: "..."
      similarity: 0.94
  ```
- Summarize clusters to `duplicates.md`.

### Code Touchpoints
- `content_processor.py`: normalized text function.
- `core.py`: post‑analysis, pre‑write clustering step.
- `vault_organizer.py`: write aliases/duplicate metadata.

### Acceptance
- Cluster formation visible; `duplicates.md` lists groups.
- Curated vault contains only canonical files unless `keep_all` flag added.

---

## 6) Model Routing Cascade with Escalation

### Goal
Use **small → medium → large** models only when necessary to reduce latency/cost while retaining accuracy on hard cases.

### Config (`config.yaml`)
```yaml
routing:
  enabled: true
  stages:
    - model: "phi3:mini"
      max_latency_ms: 800
      gray_margin: 0.05
    - model: "llama3.1:8b"
      max_latency_ms: 2500
      gray_margin: 0.03
    - model: "gpt-oss:20b"
      gray_margin: 0.02
  log_route: true
```

### Implementation (`ai_analyzer.py`)
- Implement `analyze_with_routing(note, routing_cfg)`:
  1. Score with Stage 1.
  2. If **clearly** keep/discard (outside margin) → return.
  3. Else retry with next stage; propagate reasoning and per‑stage latency.
- Persist chosen `route` on `CurationResult`.

### Acceptance
- Median latency reduced by ≥30% vs. always‑large baseline.
- Quality parity on sampled eval (§10).

---

## 7) Content‑Type Specific Rules

### Goal
Different note types need different expectations (e.g., web clippings vs. personal drafts).

### Config (`config.yaml`)
```yaml
content_types:
  PERSONAL_NOTE:
    min_length: 200
    weights: { professional_writing: 1.2, clarity: 1.1 }
    thresholds: { overall: 0.66, relevance: 0.65 }
  WEB_CLIPPING:
    min_length: 500
    weights: { credibility: 1.2, evidence_quality: 1.2 }
    thresholds: { overall: 0.70, relevance: 0.67 }
  ACADEMIC_PAPER:
    min_length: 400
    weights: { analytical_depth: 1.2, synthesis_ability: 1.1 }
    thresholds: { overall: 0.68, relevance: 0.66 }
  DEFAULT:
    min_length: 300
    weights: {}
    thresholds: { overall: 0.65, relevance: 0.65 }
```

### Implementation
- In `content_processor.py`, **detect** `content_type` (already present).
- In `ai_analyzer.py`, after raw scores:
  - Apply per‑type **weights** to compute `weighted_overall`.
- In `core.py`, compare per‑type `thresholds` and `min_length` before final decision.

### Acceptance
- Fewer false positives on clippings; better retention of insightful short drafts.
- Report shows **by‑type acceptance** improving (see §12).

---

## 8) Unicode & Boilerplate Sanitation Pass

### Goal
Remove hidden Unicode (NBSP, soft hyphen, ZWSP) and boilerplate patterns **before** AI scoring to stabilize results and dedupe.

### Config (`config.yaml`)
```yaml
sanitize:
  enabled: true
  remove_unicode:
    - NBSP
    - SOFT_HYPHEN
    - ZWSP
  boilerplate_patterns_path: "obsidian_curator/clutter_patterns.txt"
  normalize_form: "NFKC"
```

### Implementation (`content_processor.py`)
- Add `normalize_text(text, cfg)`:
  - Unicode normalize (`unicodedata.normalize`).
  - Replace specific codepoints.
  - Strip repeated headers/footers using patterns file.
- Use this in the load/clean path **before** hashing, scoring, or dedupe.

### Acceptance
- Cleaner Markdown; fewer duplicate false positives.
- Stable scores across runs.

---

## 9) Writer‑Facing Artifacts: Briefs & Stubs

### Goal
Produce **writer‑ready** outputs (briefs and optional stub drafts) per **top theme** cluster to speed up drafting.

### Config (`config.yaml`)
```yaml
writer_outputs:
  enabled: true
  briefs:
    enabled: true
    path: "metadata/briefs"
    max_claims: 7
  stubs:
    enabled: true
    path: "metadata/stubs"
    section_count: 6
```

### Implementation
- After curation, group curated notes **by theme** (you have this in `theme_classifier.py`).
- For each top theme, synthesize a **Brief** (Markdown):
  - Problem framing (3–4 lines)
  - 5–7 key claims (with note links)
  - 2–3 counterpoints/risks
  - Suggested outline (H2/H3)
- Optional **Stub**: Create a skeleton article with headings + bullet scaffolding.
- Save under configured folders.

### Acceptance
- Briefs exist for each theme with ≥5 curated notes.
- Stubs are generated when enabled; links resolve to curated notes.

---

## 10) Evaluation Harness & Regression Tests

### Goal
Keep quality stable as thresholds or models change.

### CLI
- `obsidian-curator eval --gold metadata/goldset.jsonl --report metadata/eval_report.md`

### Implementation (`tools/eval.py` or `obsidian_curator/eval.py`)
- Load gold set labels (from §2); run curation in **dry‑run** mode.
- Compute **precision/recall/F1**, **AUC**, and **acceptance rate** overall and per content type.
- Diff against a stored baseline (JSON); fail CI if F1 drop ≥5% or acceptance drift ≥10% without `--force`.
- Write a Markdown summary with confusion matrices.

### Tests (`tests/test_eval.py`)
- Unit test metric functions and report formatting.
- Fixture for small synthetic gold set.

### Acceptance
- Repeatable eval with clear pass/fail; CI gate wired (GitHub Actions).

---

## 11) Provenance, Licensing & Citation Hygiene

### Goal
Ensure clippings have **traceable sources** and flag missing/unsafe items.

### Config (`config.yaml`)
```yaml
provenance:
  required_fields: ["source_url", "author", "published_at"]
  enforce_on_types: ["WEB_CLIPPING", "PROFESSIONAL_PUBLICATION"]
  on_missing: "warn"   # "warn" | "exclude" | "triage"
  restricted_tags: ["copyrighted", "no-reuse"]
```

### Implementation
- In `content_processor.py`, **extract** provenance fields from frontmatter or detect in body.
- In `core.py`, when type matches `enforce_on_types`:
  - If missing required fields → action per `on_missing`.
- Add frontmatter key `reuse_ok: true|false` based on tags.
- During synthesis (briefs/stubs), **exclude** `reuse_ok == false` from verbatim quotes.

### Acceptance
- ≥95% of curated clippings contain required fields or are handled per policy.
- Writer outputs avoid restricted material automatically.

---

## 12) Observability: Rich Metrics & Traces

### Goal
One screen tells throughput, error modes, and curation health.

### Config (`config.yaml`)
```yaml
metrics:
  enabled: true
  path: "metadata/performance-metrics.md"
  fields:
    - "latency.total_ms"
    - "latency.ai_ms"
    - "route.stage"          # from §6
    - "decision"             # keep/discard/triage
    - "reason_top"           # primary rejection reason
    - "type"                 # content_type
    - "duplicates_cluster"   # cluster id if any
  charts: true               # optional: ASCII or simple markdown tables
```

### Implementation
- Instrument **per‑note** timings (load → sanitize → analyze → route → decide → write).
- Aggregate counters:
  - Acceptance rate (overall/by type)
  - Gray‑zone rate (from §1)
  - Escalations (from §6)
  - Duplicates removed (from §3)
  - Top rejection reasons
- Render to `performance-metrics.md` and show in GUI **Stats** panel.

### Acceptance
- Metrics file is produced each run.
- GUI shows live counters and final summary.

---

## Minimal Schema Additions (Summary)

- `TriageItem` (triage queue, §1)  
- `CalibrationConfig` + persisted coefficients (per type, §2)  
- Duplicate metadata in frontmatter (`duplicates: [...]`, §3)  
- Route info on `CurationResult` (`route.stage`, §6)  
- Per‑type rules in config (`content_types`, §7)  
- Sanitation config and normalized text function (§8)  
- Writer outputs under `metadata/briefs` and `metadata/stubs` (§9)  
- Eval report + baseline JSON (§10)  
- Provenance policy + `reuse_ok` frontmatter (§11)  
- Metrics aggregation & report (§12)

---

## Suggested PR Order

1. §8 Sanitation → §1 Triage → §7 Per‑type rules  
2. §3 Dedupe → §6 Routing  
3. §11 Provenance → §12 Metrics  
4. §2 Calibration → §10 Eval harness  
5. §9 Writer outputs (depends on clean curated set)

---

## Rollback Strategy

- Guard each feature with its **config flag**.
- Keep **unit tests** for existing behavior; add new tests behind feature flags.
- On failure in production, disable the flag and revert to stable path.

---

## Done When

- All 10 features are **behind flags**, tested, and documented.
- `docs/IMPROVEMENTS.md` updated with usage and examples.
- GUI shows **Triage** and **Metrics** panes working end‑to‑end.
