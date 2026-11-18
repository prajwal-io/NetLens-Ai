# Authentication and deployment

## Request flow

1. React uses `@supabase/supabase-js` for password signup/login, persistent sessions, refresh, logout, and password recovery.
2. Protected workspace routes and API requests require the current Supabase access token.
3. FastAPI validates each token with Supabase Auth's `/auth/v1/user` endpoint and uses only the returned Auth user ID as identity.
4. Local demo runs keep data in SQLite; each query is filtered by the verified user ID. Existing unowned SQLite records remain in place but are hidden from signed-in users.
5. Production uses Supabase Postgres through PostgREST, passing the user's token and the publishable key. PostgreSQL RLS policies scope analyses, flow features, and analyst decisions to `auth.uid()`. The `save_analysis` invoker-security RPC saves a result and its flow features in one transaction.

The health, model-info, and model-schema endpoints remain public. CSV validation/analysis, replay, history, investigation, analyst decisions, and reports require authentication. If Supabase Auth is not configured, the API fails closed; it does not create local passwords or accept demo tokens.

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
NETSIGHT_STORAGE_BACKEND=sqlite
NETSIGHT_CORS_ORIGINS=["http://127.0.0.1:5173","http://localhost:5173"]
```

Then run the backend from `backend/` and Vite from `frontend/` using [the local setup guide](phase-1.md). Local email confirmations are delivered to Supabase's local Inbucket UI at `http://127.0.0.1:54324`. Prepare the local Supabase containers and model artifact before the presentation; after that, the laptop demo can run without a cloud Auth connection.

## Hosted setup

Create a dedicated Supabase project for NetLens AI. Link this repository with the Supabase CLI and apply `supabase/migrations/20261118120000_create_user_owned_analyses.sql` using `supabase db push`. Configure email/password Auth and add the exact frontend origins plus `/auth/callback` and `/auth/reset-password` to Auth's allowed redirect URLs. Set the production Site URL to the Vercel origin.

Configure Vercel with:

- `VITE_API_BASE_URL`: the HTTPS Render/Railway API URL ending in `/api/v1`.
- `VITE_SUPABASE_URL`: the dedicated Supabase project URL.
- `VITE_SUPABASE_PUBLISHABLE_KEY`: the project's publishable (or legacy anon) key.

Configure the backend with:

- `NETSIGHT_SUPABASE_URL` and `NETSIGHT_SUPABASE_PUBLISHABLE_KEY` for Auth verification and user-scoped PostgREST access.
- `NETSIGHT_STORAGE_BACKEND=supabase` to select PostgreSQL/RLS for saved results.
- `NETSIGHT_CORS_ORIGINS` as a JSON array containing only deployed Vercel origins, for example `["https://your-app.vercel.app"]`.
- `NETSIGHT_MODEL_ARTIFACT_PATH` pointing to the evaluated `netsight-model.joblib` artifact.

Never set a Supabase `service_role` or secret key in Vite variables or expose it to the browser. The backend uses the caller's token, so Postgres RLS remains active. Vercel builds must be redeployed after changing `VITE_*` variables.

## Deployment limits

The repository includes a Vercel SPA rewrite and Render service definition, but no hosted NetLens Supabase project or deployment credentials are configured in this workspace. The model artifact is intentionally gitignored (about 48 MB); provision the evaluated file in private backend artifact storage and set its path before the API can serve real predictions. Hosted deployment, real email delivery, and live Postgres/RLS execution must be verified after those account-specific settings are supplied.
