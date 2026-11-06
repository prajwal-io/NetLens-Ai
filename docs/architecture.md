# Phase 1 architecture

React Router provides six independent workspace routes. Shared panels, status handling, fixtures, and the typed API client separate interface concerns. Vite bundles fonts locally; no CDN is needed at runtime. Tailwind v4 is wired through the Vite plugin, alongside custom layout tokens.

FastAPI routes delegate CSV inspection to a validation service and return typed response schemas. Settings control local CORS, upload limits, and SQLite location. Lifespan initializes a versioned SQLite schema with foreign keys and WAL; validation does not persist uploaded traffic. No inference endpoints or trained artifacts are included.

## CSV contract: foundation-flow-v1

UTF-8 CSV, optionally with BOM; headers are trimmed and must be unique. Required columns: Destination Port, Flow Duration, Total Fwd Packets, Total Backward Packets. All required values must be finite and nonnegative. Ports and packet counts are integers; ports may not exceed 65535. Flow Duration is in microseconds. Additional columns are accepted and returned in the preview. This is a Phase 1 subset, not the eventual model feature contract.

Maximum file payload: 5 MiB; maximum nonempty data rows: 50,000. Parsing stops at the row limit. Preview contains at most five rows. CSV values are rendered as text. Success returns row_count, columns, preview, schema_name, valid and message. Failures use {error: {code, message}} with HTTP 413, 415, or 422. Missing multipart files return 422. Unexpected server errors return a generic 500 while server logs retain details.

## Scope and transparency

Dashboard totals are computed from fixture time buckets; the recent-flow table is an illustrative subset. All sample classifications are labeled. Model Lab has no fabricated metrics. Network Pulse and Reports are honest foundations with later-phase empty states. Historical replay, inference, investigation details, analysis persistence, and exports are deferred to their README phases.

Health is polled every 30 seconds and can be manually retried. Request timeout is 15 seconds. Upload validation has separate pending, success, and recoverable error states. A backend outage does not replace sample values with invented live data.

## Visual direction

Framed sheet, seed 439000391. Preserve the README palette and typography. The blue traffic series and custom network mark identify NetSight; neutral chrome keeps attention on evidence. Main question: what does this sample traffic window contain, and is the local workspace ready for a dataset?
