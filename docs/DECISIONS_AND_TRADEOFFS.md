# Decisions & trade-offs

A short record of the engineering choices behind this build and why. The FE BAR rewards this explicitly ("Why this approach and not another?").

## 1. Lakebase first, then Lakehouse and Lakeflow
**Chose:** stand up the Lakebase claims ODS behind Harbor first, then layer analytics and streaming.
**Why:** it matches the customer's own phasing, and the operational store is what the business feels first. Proving current claim state in the application funds the analytics and AI phases. **Trade-off:** a second engine to operate, justified by OLTP latency and the hybrid model.

## 2. Hybrid relational + JSON in one store
**Chose:** relational columns for structured claim fields, a JSONB column for the variable long tail, queried together, with a GIN index over the JSON.
**Why:** a claim carries thousands of elements; a pure relational model drops the tail, a pure document model loses query discipline. Both in one store keeps the claim whole and lets Harbor filter on nested elements. **Trade-off:** more schema design up front.

## 3. Certified metric views vs. prompting the agent over raw tables
**Chose:** define certified metric views (disposition rate, downstream-action-fired rate, dollar exposure) with `MEASURE()` semantics.
**Why:** an agent that computes KPIs ad-hoc drifts. Certified metrics give one governed definition Genie and the dashboard both use. **Trade-off:** more modeling; worth it for trust and reproducibility.

## 4. Declared PK/FK (RELY) graph vs. leaving joins to the model
**Chose:** declare PK/FK constraints as `RELY` (zero-orphan verified at generation).
**Why:** Genie infers joins from real relationships instead of guessing, and the optimizer uses them. **Trade-off:** the data must stay clean enough to declare RELY honestly.

## 5. PHI masked at the governance layer, not at query time
**Chose:** UC column masks on member name, SSN, DOB, gated by group membership.
**Why:** the mask becomes a property of the column, so it holds across notebook, Genie, and model serving with no bypass, which is what survives an audit. **Trade-off:** masks authored and tested per column.

## 6. Both a Gen AI agent and a Genie agent (plus an ML model)
**Chose:** a reasoning agent (triage on a single claim), a Genie agent (population analytics over certified metrics), and a trained ML model (manual-review score).
**Why:** claims work spans single-record decisions and population questions; they are different question shapes served by different tools, over the same governed schema. **Trade-off:** more surface to build, but it is the difference between a demo and an end-to-end system, and it mirrors what a passing reference build shipped.

## 7. Event-driven disposition vs. batch
**Chose:** a disposition fires a governed downstream action through orchestration.
**Why:** the customer's pain is that nothing reacts when a claim's status changes. A batch job scraping a table reintroduces the lag. **Trade-off:** orchestration to build and monitor.
