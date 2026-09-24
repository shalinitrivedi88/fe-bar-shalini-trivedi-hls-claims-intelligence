# FE BAR submission checklist

Status of everything the submission form asks for. **Nothing has been submitted** — this is prep.

## Ready in this repo (scaffold)
- [x] **Structure** — 6 connected layers under `01_`…`06_` plus `07_ml_model`, one governed schema.
- [x] **Integrated narrative** — `README.md` leads with the business outcome, shows the connected data flow, and maps every layer.
- [x] **Six form answers drafted** — `SUBMISSION.md` (customer, vertical, challenge, solution, AI tools & trade-offs, outcomes).
- [x] **Decisions & trade-offs** — `docs/DECISIONS_AND_TRADEOFFS.md`.
- [x] **Presentation deck** — `deck/DECK.md` (outcome-led; exec + technical framing).
- [x] **Synthetic data only** — no real customer data; fictional customer name (Cascade Benefit Systems).

## Executed on fevm (evidence committed as text)
> The FE BAR Build domain requires **evidence the build actually ran, committed as text** — the #1 pass-blocker. Status below reflects the 2026-09-23 run.
- [x] **Generate + ingest data** — 50k claims + full book generated on serverless; row counts in `evidence/RUN_EVIDENCE.md` §1.
- [x] **Apply governance** — 5 PK + 5 FK RELY declared; PHI masks verified (masked read); §2-§3.
- [x] **Deploy Lakebase** — project `cascade-claims-ods` created, 500 rows seeded, hybrid relational+JSON query verified; `evidence/LAKEBASE_DEPLOYMENT.md`.
- [x] **Certified views** — dollar exposure + disposition-action gap captured; §4. (Metric-view `MEASURE()` YAML deferred; plain certified views used.)
- [x] **Genie trace** — space created, live NL→SQL→answer over the certified view; §6.
- [x] **Triage agent** — invoked the governed serving endpoint on a real claim; §5.
- [x] **App** — `claims-ops-console` deployed (RUNNING), API returns governed data; `evidence/APP_DEPLOYMENT.md`.
- [~] **ML model** — trained + scored 50k claims (`evidence/ML_MODEL.md`); UC registration + serving blocked by the shared-metastore 5,000-model quota (env limit, not code) — re-run `REGISTER_UC=true` when quota frees.

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
