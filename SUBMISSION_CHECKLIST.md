# FE BAR submission checklist

Status of everything the submission form asks for. **Nothing has been submitted** — this is prep.

## Ready in this repo (scaffold)
- [x] **Structure** — 6 connected layers under `01_`…`06_` plus `07_ml_model`, one governed schema.
- [x] **Integrated narrative** — `README.md` leads with the business outcome, shows the connected data flow, and maps every layer.
- [x] **Six form answers drafted** — `SUBMISSION.md` (customer, vertical, challenge, solution, AI tools & trade-offs, outcomes).
- [x] **Decisions & trade-offs** — `docs/DECISIONS_AND_TRADEOFFS.md`.
- [x] **Presentation deck** — `deck/DECK.md` (outcome-led; exec + technical framing).
- [x] **Synthetic data only** — no real customer data; fictional customer name (Cascade Benefit Systems).

## Must run on the workspace before submitting (this is where the pass is won)
> The FE BAR Build domain requires **evidence the build actually ran, committed as text** — this is the #1 pass-blocker. The scaffold is not enough on its own.
- [ ] **Generate + ingest data** — run `01_lakeflow_ingest/generate_claims_data.py` and the pipeline on `fevm`; capture row counts into `evidence/RUN_EVIDENCE.md`.
- [ ] **Apply governance** — run `02_unity_catalog_governance/*.sql`; capture the PK/FK constraint listing and a PHI-mask before/after into evidence.
- [ ] **Deploy Lakebase** — create the `cascade-claims-ods` instance, seed it, run the hybrid relational+JSON query; capture into `evidence/LAKEBASE_DEPLOYMENT.md`.
- [ ] **Certified metric views** — run the disposition-rate / downstream-action-fired / dollar-exposure queries with `MEASURE()`; capture results.
- [ ] **Genie trace** — ask a claims question via the Genie Conversation API; capture the NL→SQL→answer trace verbatim into evidence §6.
- [ ] **Triage agent** — deploy and invoke; capture a sample classification + next-action output.
- [ ] **ML model** — train, register in UC, score, serve; capture metrics into `evidence/ML_MODEL.md` (report AUC honestly).
- [ ] **App** — deploy the Claims Operations Console; confirm it reads the governed SQL and proxies chat.

## Form actions (I won't submit for you)
- [ ] **Repo pushed** to `shalinitrivedi88/fe-bar-shalini-trivedi-hls-claims-intelligence` (public; internal-process notes stay in the Google Doc, not here).
- [ ] **GitHub repo link** — paste the repo URL for reviewer reference.
- [ ] **Select the local repo folder** — point the form's "Choose repo folder" at this directory.
- [ ] **Paste the six answers** from `SUBMISSION.md`.
- [ ] **Attach the deck** — attach `deck/DECK.md` or export to PDF.
- [ ] **Conversation ID (optional)** — this build session's ID.
- [ ] **Attestation** — check the box and type your full name.

## Optional strengthening
- [ ] Export the deck to a Databricks-themed Google Slides deck.
- [ ] Add a per-claim UC-function output to `evidence/` as agent-tool proof.
- [ ] Add a Lakebase synced-table example showing the ODS staying in step with the lake.
