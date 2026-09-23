# App overview — Claims Operations Console

The console is the business-facing surface of the build. It reads the one governed schema and proxies chat to the claims foundation model.

## Screens / endpoints
- **Triage queue** (`/api/triage-queue`): claims flagged for manual review, highest billed first. Wire to `claim_review_priority.manual_review_score` (07) and the Lakebase `claim_status.triage_score` (04) for the full prioritization story.
- **Disposition gap** (`/api/disposition-gap`): the share of dispositions that never fired a downstream action, by disposition. This is the event-blindness metric.
- **Ask** (`/api/chat`): a plain-English question routed to the foundation model through the serving layer.

## Who uses it
- Renee (VP Claims Products): watches the disposition gap and the freshness of claim state.
- A reviewer: works the triage queue top-down.
- Daniel (analytics): uses Ask, or the Genie space, for governed self-serve.

## Auth
The app runs as its service principal against the SQL warehouse and serving layer. Grant the SP read on `claims_intelligence` and use of warehouse `a2fb11a86770690f`.
