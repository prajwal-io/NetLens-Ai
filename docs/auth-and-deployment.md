# Authentication and deployment

## Request flow

1. React uses `@supabase/supabase-js` for email-code signup/sign-in, persistent sessions, refresh, logout, and password recovery.
2. Protected workspace routes and API requests require the current Supabase access token.
3. FastAPI validates each token with Supabase Auth's `/auth/v1/user` endpoint and uses only the returned Auth user ID as identity.
4. Local demo runs keep data in SQLite; each query is filtered by the verified user ID. Existing unowned SQLite records remain in place but are hidden from signed-in users.
5. Production uses Supabase Postgres through PostgREST. Reads and deletes use the verified user's token and owner-scoped RLS. Validated writes use a server-only Supabase secret key after the API verifies the caller; the database rejects client-role inserts and updates.

## Data access controls

RLS is PostgreSQL authorization policy, not an application-side filter. Policies scope analysis, flow, and response-decision rows to `auth.uid()`. Table grants separately limit which operations each role can attempt: signed-in users can read their own data and delete their own analyses or decisions; direct client writes are revoked. The grant-hardening migration also removes `TRUNCATE` and other unneeded table privileges. Backend `service_role` writes bypass RLS, so its secret must stay server-side and API writes must use the ID from a verified Auth token. The pgTAP checks are in `supabase/tests/analysis_table_privileges_test.sql`.

## URL analysis and packet captures

The authenticated `/api/v1/url/check` endpoint validates a public HTTP/HTTPS URL, runs the separate URL-only logistic-regression model, resolves public DNS, then makes a bounded HTTP `HEAD` check. The probe pins the resolved public addresses, blocks private/reserved destinations, follows at most four redirects, accepts only ports 80/443, and never downloads a page body. The model uses 22 lexical features recomputed from the raw URL and was trained with domain-grouped splits on the [UCI PhiUSIIL dataset](https://archive.ics.uci.edu/dataset/967/phiusil+phishing+url+dataset); it is an investigation signal rather than a confirmed verdict. The model metrics and limitations travel with its JSON artifact.

The URL model is not the UNSW-NB15 flow model: a URL does not contain the 42 network-flow fields needed by the Random Forest. Packet-derived records likewise do not satisfy that flow contract and are not classified by it. Traffic Analyzer accepts `.pcap` and `.pcapng` up to 5 MiB; the parser caps work at 100,000 packets and 10,000 flows, keeps results in the response only, and extracts bounded TCP/UDP IPv4/IPv6 flow counters. The website cannot sniff a user's network interface; live capture requires a separately installed, permissioned sensor. The bundled capture is synthetic and uses documentation-only IP addresses.

Traffic Analyzer accepts `.pcap` and `.pcapng` up to 5 MiB. The parser caps work at 100,000 packets and 10,000 flows, keeps results in the response only, and extracts bounded TCP/UDP IPv4/IPv6 flow counters. Packet-derived records do not match the Random Forest's 42-feature UNSW-NB15 contract, so the parser deliberately does not classify them with that model. The website cannot sniff a user's network interface; live capture requires a separately installed, permissioned sensor. The bundled `frontend/public/demo-capture.pcap` is synthetic and uses documentation-only IP addresses.

The health, readiness, model-info, and model-schema endpoints remain public. Render checks `/api/v1/ready`, which confirms the evaluated model and, in Supabase mode, that the migrated analyses table is reachable. CSV validation/analysis, replay, history, investigation, analyst decisions, and reports require authentication. If Supabase Auth is not configured, the API fails closed; it does not create local passwords or accept demo tokens.

## Local setup

Use a local Supabase stack for predictable demo accounts and keep SQLite as the local history store. Install Docker Desktop and the Supabase CLI once, then from the repository root:

```powershell
supabase start
supabase db reset
supabase status -o env
```

Copy the local API URL and anon key reported by `supabase status -o env` into `frontend/.env.local` and `backend/.env` (the local anon key is a publishable client key):

```dotenv
VITE_API_BASE_URL=/api/v1
VITE_SUPABASE_URL=http://127.0.0.1:54321
VITE_SUPABASE_PUBLISHABLE_KEY=<local-anon-key>
```

```dotenv
NETSIGHT_SUPABASE_URL=http://127.0.0.1:54321
NETSIGHT_SUPABASE_PUBLISHABLE_KEY=<local-anon-key>
NETSIGHT_SUPABASE_SECRET_KEY=<local-service-role-key>
NETSIGHT_STORAGE_BACKEND=sqlite
NETSIGHT_CORS_ORIGINS=["http://127.0.0.1:5173","http://localhost:5173"]
```

Then run the backend from `backend/` and Vite from `frontend/` using [the local setup guide](phase-1.md). Local email confirmations are delivered to Supabase's local Inbucket UI at `http://127.0.0.1:54324`. Prepare the local Supabase containers and model artifact before the presentation; after that, the laptop demo can run without a cloud Auth connection.

## Hosted setup

Create a dedicated Supabase project for NetLens AI. Link this repository with the Supabase CLI and apply all files in `supabase/migrations` using `supabase db push`. Configure email/password Auth and add the exact frontend origins plus `/auth/callback` and `/auth/reset-password` to Auth's allowed redirect URLs. Set the production Site URL to the Vercel origin.

For hosted confirmation and password-reset emails, configure a custom SMTP provider in Supabase Auth. The built-in sender is intended for development and may deliver only to project team addresses; check Auth logs and provider delivery logs when messages do not arrive. Keep email confirmation enabled for production and configure SPF/DKIM for the sender domain.

For email-code verification, configure custom SMTP first, then edit **Authentication → Email Templates → Confirm signup** and **Magic link**. Use a subject such as `Your NetLens AI sign-in code` and a body such as:

```html
<h2>Your NetLens AI sign-in code</h2>
<p>Enter this one-time code in the sign-in screen. It expires shortly.</p>
<p style="font-size: 28px; font-weight: bold; letter-spacing: 6px">{{ .Token }}</p>
<p>If you did not request this, you can ignore this email.</p>
```

Remove `{{ .ConfirmationURL }}` from those templates so Supabase sends the code. The code is entered on the app's verification screen and is never rendered by the app before entry. OTP does not bypass SMTP restrictions.

To copy existing owned SQLite history before switching the backend to Supabase, set `NETSIGHT_SUPABASE_URL` and the backend-only `NETSIGHT_SUPABASE_SECRET_KEY`, then run from `backend/`:

```powershell
python -m scripts.migrate_sqlite_to_supabase
```

The command copies only rows with an owner ID, including flow features and analyst decisions. It can be rerun safely, and it retains the SQLite source. Unowned legacy rows stay local and hidden. Reports are generated from the migrated analysis and decisions, so they need no separate table or import.

Configure Vercel with:

- Set the project Root Directory to `frontend`; Vercel reads `frontend/vercel.json` there. It installs with `npm ci`, builds with `npm run build`, publishes `dist`, and rewrites app routes to the SPA entry point.

- `VITE_API_BASE_URL`: the HTTPS Render/Railway API URL ending in `/api/v1`.
- `VITE_SUPABASE_URL`: the dedicated Supabase project URL.
- `VITE_SUPABASE_PUBLISHABLE_KEY`: the project's publishable (or legacy anon) key.

Configure the backend with:

- The root `render.yaml` defines the Render web service. It pins Python 3.12.11, installs `requirements.lock.txt`, binds Uvicorn to Render's `$PORT`, and checks readiness at `/api/v1/ready`.

- `NETSIGHT_SUPABASE_URL` and `NETSIGHT_SUPABASE_PUBLISHABLE_KEY` for Auth verification and user-scoped PostgREST access.
- `NETSIGHT_SUPABASE_SECRET_KEY` for backend-only writes after API authorization. Keep it out of Vite variables and source control.
- `NETSIGHT_STORAGE_BACKEND=supabase` to select PostgreSQL/RLS for saved results.
- `NETSIGHT_CORS_ORIGINS` as a JSON array containing only deployed Vercel origins, for example `["https://your-app.vercel.app"]`.
- `NETSIGHT_MODEL_ARTIFACT_PATH` pointing to the evaluated `netsight-model.joblib` artifact.
- `NETSIGHT_MODEL_ARTIFACT_URL` set to a private HTTPS download link for that artifact, and `NETSIGHT_MODEL_ARTIFACT_SHA256` set to its SHA-256 digest. The Render start command downloads the artifact and checks the digest before starting the API. Keep the URL private and valid for deploys/restarts; the artifact is too large for Render secret files and remains out of Git.
Never set a Supabase `service_role` or secret key in Vite variables or expose it to the browser. Backend writes use the secret key and must include the verified user ID; reads continue to use the caller's token under RLS. Vercel builds must be redeployed after changing `VITE_*` variables.

## Deployment limits

The repository includes a Vercel SPA rewrite and Render service definition, but no hosted NetLens Supabase project or deployment credentials are configured in this workspace. The model artifact is intentionally gitignored (about 48 MB); Render now requires a private artifact URL and matching SHA-256 before starting. Hosted deployment, real email delivery, and live Postgres/RLS execution must be verified after those account-specific settings are supplied.
