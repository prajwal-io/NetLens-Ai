# Frontend completion: 18-area checklist

| Area | Delivered |
|---|---|
| 1 Navigation | Six tool routes, active states, mobile/tablet disclosure, breadcrumb links, back/forward-compatible investigation URLs, and helpful 404 view. |
| 2 Responsive layouts | Tested 320px phone, 390px phone, 844px landscape, 720px zoom-equivalent reflow, tablet and desktop layouts. |
| 3 Design consistency | Shared typography, controls, tables, panels, metadata, and state components retained across all routes. |
| 4 Background | Two edge-only signal passes repeat every 14 seconds, staggered seven seconds apart; pause preference, hidden-document suspension, reduced-motion support. |
| 5 Motion | Short feedback using existing tokens, no data-count animation, CSS background loop without per-frame JavaScript. |
| 6 Dashboard | Persistent chart window, explicit full-sample totals, point inspection, accessible data table, actual backend status/freshness/retry. |
| 7 Uploads | File metadata, replace/remove, drag feedback, extension/size/empty-file prechecks, actual XHR transfer progress, indeterminate server validation, cancellation, retry and duplicate-request guard. |
| 8 Investigation | Search, classification filter, sort, result count, reset, URL state, remembered preferences, selected details and focused mobile view with back control. |
| 9 Network | Persistent device and zoom, zoom centered on selection, reset, pause, keyboard nodes, readable details and conceptual-source labeling. |
| 10 Model Lab | Clear planned metadata, unavailable evaluation state and limitations. Actual model metrics require Phase 2 artifacts and APIs; none are invented. |
| 11 Reports | Real session validation receipts with metadata preview, search, JSON download, clear controls and export-failure feedback. Prediction CSV/PDF exports and server analysis history remain later backend phases. |
| 12 State | Session preferences and URL filters survive navigation/reload; in-memory fallback works with blocked storage. Raw files and traffic rows are not persisted. |
| 13 Accessibility | Focus states, keyboard controls, labeled filters, captions, chart alternative, reduced motion, meaningful statuses and responsive targets. Automated scans pass; spoken output on physical assistive technology was not manually tested. |
| 14 Performance | Route splitting, lean Motion feature set, local assets, native SVG charts, visibility-aware health polling and animation lifecycle cleanup. |
| 15 Reliability | Page error boundary/retry, shared route skeleton, offline/online recovery, timeout handling, request cancellation, unmount cleanup, malformed-response errors. |
| 16 Content/trust | Sample, conceptual, validation-only and future ML features are distinguished throughout. Receipt timestamp is browser receipt time, not an analysis timestamp. |
| 17 Production | Environment example, same-origin API proxy, preview security headers, metadata/favicon/robots, direct-route checks and deploy/nginx.conf.example. Nothing deployed externally. Configure TLS and hosting for an actual public release. |
| 18 Verification | Chrome smoke/completion/recovery checks, Edge completion checks, 17 backend tests, 14 route/viewport axe scans, visual inspection and deployment smoke checks. |

## Verification results
- Production TypeScript/Vite build: passed.
- Chrome smoke, completion, and recovery tests: passed.
- Microsoft Edge completion tests: passed.
- Backend tests: 17 passed; one upstream TestClient deprecation warning.
- WCAG-tagged axe scans: zero violations on seven routes at desktop and phone widths; expanded-menu accessibility also passed.
- Visual inspector: zero failures for landing and dashboard at desktop, tablet and phone.
- Real receipts were checked against the backend response and downloaded as JSON: 3 rows, no predictions, no saved traffic preview.
- Security headers, direct SPA links, deep links and same-origin health requests: passed.
- Prior performance reports remain a baseline. A new full Lighthouse pass was not run for this final feature set after the user requested a faster finish.

## Run
Keep FastAPI on port 8000.
From frontend: npm.cmd run dev for port 5173.
Production: npm.cmd run build then npm.cmd run preview -- --port 4177.
Preview: http://127.0.0.1:4177/

Tests use AUDIT_URL to select a running frontend. completion-tests.mjs and recovery-tests.mjs accept BROWSER_EXECUTABLE for Chrome or Edge.

## Boundary
This completes the frontend foundation and its current-data workflows. A trained model, inference, actual historical replay, evaluation outputs and prediction report APIs remain backend roadmap work. The interface does not simulate them.

## Frontend finalization / November 6
Frontend-only scope confirmed by the user. Final fixes:
- Malformed health and validation responses are rejected before rendering; preview cells and column contracts are checked.
- Invalid flow deep links show a missing-record state instead of an unrelated fallback record.
- Receipt search and selection persist for the tab session; filtered empty states remain in receipt context.
- Receipt download URLs are cleaned up even if browser download preparation fails.
- Receipt singular/plural labels and clear-search behavior corrected.

Verified production build, 17 backend tests, full interaction suite, targeted malformed-response/deep-link tests, and zero automated accessibility violations across all seven routes at desktop and phone widths. The local backend was restarted.

Current preview: http://127.0.0.1:4177/
Backend: http://127.0.0.1:8000/
ML inference, true historical replay, and prediction report APIs remain outside this frontend-only finalization.

## Theme and telemetry background / November 6
The interface now uses a near-black canvas, blue network signals, and red suspicious-flow marks. The original logo artwork remains unchanged and sits on a small light panel for contrast. Slow packet-like text falls in eight narrow streams at desktop edges and two at phone widths. The center remains clear. The motion pauses when requested, when the page is hidden, and when reduced motion is enabled.

Verified the production build, all seven routes at desktop and phone sizes, the browser interaction suite, and the FastAPI health and CSV-validation endpoints. Accessibility scans report zero violations at both tested widths. Preview: http://127.0.0.1:4177/.
