# Roleplay: tell-show-tell script + objection handling

For the FE BAR live presentation. Audience: a business persona (VP Claims Products /
CFO angle) and a technical persona (Chief Data Platform Architect / CISO angle).
Cascade Benefit Systems is fictional; all data is synthetic. Keep it tight, about 5 minutes,
then handle objections.

## TELL (about 1 minute) — the problem and the value

"Cascade processes 250 million claims a year on a DB2 and CICS mainframe. The mainframe
adjudicates fine, but every downstream consumer, the member application and the analysts,
reads a nightly batch extract that is already a day stale. Nothing fires when a claim is
disposed, and cross-claim questions are multi-week SQL tickets.

On our synthetic book, $23.9M sits in the denied and pending rework pool, and about 40% of
dispositions never fired a downstream action. Recovering even 10% of that pool is roughly
$2.4M a year. I built one governed platform on Databricks that puts the current claim in the
application, acts on a disposition the moment it happens, and lets analysts self-serve, all
over one governed schema."

## SHOW (about 3 minutes) — the connected journey, one governed schema

Open the Claims Operations Console (the Databricks App) and walk the flow, naming the layer
behind each screen so the journey is obvious, not six demos stitched together.

1. **Current claim state** (Lakebase). "The app reads the Lakebase claims ODS, relational
   columns plus a JSON long tail, so this is the live claim, not last night's extract."
2. **The gap, quantified** (Unity Catalog certified metric views). "This panel is the
   downstream-action-fired rate by disposition, off a certified metric view. Partially Paid
   is the worst at 59%."
3. **Ask in plain English** (Genie). Type: "downstream-action-fired rate by disposition?"
   "Genie writes governed SQL using MEASURE over the certified metric, no ticket."
4. **Triage a claim** (Gen AI agent). "The agent scored claim C000022633 at 0.834 and
   proposed appeal-route, citing the timely-filing denial. It is a tool-calling ResponsesAgent."
5. **Find precedent** (Lakebase pgvector + BM25). Search: "denied specialist claim not
   medically necessary". "Hybrid semantic plus keyword search over case narratives, fused
   with reciprocal rank, finds similar prior cases instantly."
6. **Governance** (Unity Catalog). "PHI is masked at the governance layer, so member name,
   SSN, and DOB are masked in the app, in Genie, and in model serving, one policy, no bypass."

## TELL (about 1 minute) — outcomes and the ask

"Every layer read the same governed schema, so the app, Genie, the agent, and the model all
speak one certified definition. The value maps to owners: claim freshness and the disposition
gap for the VP of Claims Products, the $23.9M rework exposure for the CFO, one PHI story for
the CISO. The ask: green-light a scoped pilot on one line of business, point Lakeflow at a
de-identified extract, stand up the Lakebase ODS behind the member app, and measure claim-to-
availability, disposition-to-action, and analyst self-serve over one quarter against the
$23.9M baseline. Low incremental cost, it reuses the lakehouse and serverless compute you own."

---

## Objection handling — business persona (VP Claims Products / CFO)

**"Is this real or a roadmap?"**
Real and running on a workspace. The data generated, the governance, Lakebase, Genie, the app,
and the model all executed live, and the evidence is committed as text in the repo. The one
thing not yet live is the served model endpoint, which is blocked by a shared-metastore quota,
not by the build. It is one command away.

**"Where is the dollar value?"**
$23.9M sits in the denied and pending pool on our synthetic book. Recovering 10% is about $2.4M
a year, and we remove the manual chase on ~17,000 disposition events. That is an estimate on
synthetic data; the pilot measures the real recovery against that baseline.

**"Do I have to rip and replace the mainframe or my application?"**
No. The mainframe keeps adjudicating. Databricks is where the claim becomes a product. The
application reads the Lakebase ODS instead of a nightly extract, and that is the only change
your members feel.

**"How fast to value?"**
The pilot is one line of business: ingest a de-identified extract, stand up the ODS behind the
app, and you see current claim state and the disposition gap in the first cycle, measured over
a quarter.

## Objection handling — technical persona (Chief Data Platform Architect / CISO)

**"What does a standalone Lakebase deployment actually take?"**
An Autoscaling Postgres project, a production branch, and a primary endpoint with scale-to-zero,
auth by short-lived OAuth token. We run the hybrid model in it: relational columns plus JSONB
with a GIN index, and pgvector for search. It is provisioned and seeded in the build.

**"Is the hybrid model real, or a slide?"**
Real. One query returns relational columns and nested JSON together, and a JSON containment
filter over the GIN index finds the coordination-of-benefits claims. It is in the evidence.

**"Where is PHI masked, and can it be bypassed?"**
Masked at the governance layer with Unity Catalog column masks, so it is a property of the
column. The same masked result comes back in a notebook, in Genie, and through model serving.
Members of one group see cleartext; no query routes around it. Verified on every member row.

**"Why Lakebase and not serve from the lakehouse?"**
Right engine per job. The application needs OLTP-latency reads and a variable JSON long tail,
which is a Postgres plus JSONB job. Analytics stays on the lakehouse. One journey, two engines.

**"GA versus preview, and the OLTP/OLAP convergence?"**
I separate those honestly. Lakebase Autoscaling, Unity Catalog, Genie, and Model Serving are
the GA spine here. Metric-view semantics and the convergence direction I would confirm against
current docs per your target region before we architect around them, rather than assert.

**"Your model AUC looks too good."**
It is 0.9241 and I report it as optimistic by construction: the synthetic label is partly
derived from features the model also sees. On real claims the label is independent and AUC
would be lower. The point here is the end-to-end MLOps pattern and the prioritization, not the
score. A production model needs independent validation.
