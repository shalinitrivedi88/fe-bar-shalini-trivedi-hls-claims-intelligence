---
title: Real-Time Claims Intelligence
subtitle: From nightly batch to current claim state, governed, for a health-plan claims processor
audience: Executive sponsor (VP Claims Products) + Technical owner (Chief Data Platform Architect)
---

# Real-Time Claims Intelligence
### Current claim state, governed, in the application — not yesterday's extract

A claims build on Databricks for a regional health-plan claims processor.
*(Cascade Benefit Systems is fictional; synthetic data; real public code taxonomies.)*

---

## Slide 1 — The business problem

**Whose problem: the VP of Claims Products.** Scorecard: claim-to-availability latency, disposition-to-action time, analyst self-serve rate.

**Claims are trapped in a mainframe built for adjudication, not products or analytics.**

- The Harbor application and the analysts read a nightly batch extract, already a day stale.
- A single claim carries thousands of data elements; the batch loop breaks on every schema change.
- When a claim reaches a disposition, nothing fires the action that should follow.

> VP of Claims Products: claim freshness, disposition-to-action, self-serve analytics.
> CFO: denied and pended dollar exposure rolls into the rework pool.
> CISO: PHI governance across the operational store and the lake (HIPAA, HITRUST).

---

## Slide 2 — The stakes

On the synthetic book analyzed (executed live; figures in `evidence/RUN_EVIDENCE.md`):

| Metric | Value |
|---|---|
| Total billed | *(from evidence)* |
| Denied + pending dollar pool (rework) | *(from evidence)* |
| Dispositions with no downstream action fired | *(the event-blindness gap)* |
| Claims flagged for manual review | *(from evidence)* |

The denied and pending pool rolls into the **CFO's** exposure; claim freshness and the action gap land on the **VP of Claims Products'** scorecard. That is what we move.

---

## Slide 3 — The solution: one connected data journey

```
raw synthetic claims (837/835, hybrid relational + JSON)
  → Lakeflow (ingest + stream disposition events)
  → Unity Catalog (govern: PK/FK RELY, certified metric views, PHI masks)
  → Lakebase (claims ODS: current state to the Harbor app)
  → Gen AI triage agent  +  Genie agent (NL → certified SQL)
  → Databricks App (Claims Operations Console + chat)
  → ML model (manual-review score → reviewer prioritization)
```

**Every layer reads the same governed schema.** The app, the Genie agent, the triage agent, and the model all speak one set of certified definitions.

---

## Slide 4 — What the team actually gets

- **Current claim state in Harbor:** the app reads Lakebase, not last night's extract.
- **Ask in plain English:** "downstream-action-fired rate by disposition?" → governed answer via `MEASURE()`, in seconds.
- **Act on disposition:** the triage agent scores each claim and proposes the next action; the disposition can fire it.
- **Prioritize the queue:** the ML score surfaces the highest-risk claims first.

---

## Slide 5 — Proof it runs (not a mockup)

Committed as text in `evidence/`:
- Governed tables populated (row counts).
- PK/FK RELY constraints live — the join graph the agent trusts.
- PHI mask holding across notebook, Genie, and serving (before/after).
- A live Genie NL → `MEASURE()` SQL → grounded answer trace.
- Lakebase hybrid relational + JSON query returning current claim state.

---

## Slide 6 — Business outcomes (mapped to who owns them)

- **Claim-to-availability latency (VP Claims Products):** nightly batch → current state in Harbor.
- **Disposition-to-action (VP Claims Products):** close the event-blindness gap.
- **Denied + pended exposure (CFO):** see where the rework pool concentrates and cut it.
- **PHI governance (CISO):** one mask across every reader, lineage an auditor can trace.
- **Scales the team, not headcount:** analysts self-serve; reviewers start highest-risk.

---

## Slide 7 — For the technical stakeholder

- **Governance-first:** certified metric views + declared RELY keys → reproducible, Genie-trusted joins.
- **Right engine per job:** analytics on the lakehouse; OLTP + JSON on Lakebase.
- **Hybrid model, one store:** relational columns + JSONB for the claim's long tail.
- **Governed AI:** foundation-model routing through the serving layer (Unity Gateway) with usage and cost visible.

---

## Slide 8 — The ask

Green-light a scoped pilot on one line of business:

1. Point Lakeflow at a de-identified extract.
2. Stand up the Lakebase ODS behind Harbor for one claim segment.
3. Measure the VP's metrics over one quarter: claim-to-availability latency, disposition-to-action time, and analyst self-serve rate, with the CFO's exposure in the rework pool reported.

**Low incremental cost — it reuses the governed lakehouse and serverless compute you already own.**
