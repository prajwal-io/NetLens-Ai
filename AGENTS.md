# NetLens AI: Agent Rules

Project: ML network traffic analysis platform.
Stack: React + TypeScript + Vite + Tailwind (frontend), FastAPI +
Scikit-learn Random Forest (backend), UNSW-NB15, Supabase (auth/DB).

## Always
- Keep design, spacing, naming, and terminology consistent across all
  modules (Command Center, Network Pulse, Traffic Analyzer, Threat
  Investigation, Model Lab, Reports, History).
- Every page, chart, table, and CSV/PDF report must show real data.
  No placeholders, no dead buttons, no broken states.
- Don't break existing features. Run the build, lint, and tests after
  every change.
- Keep the honest limitations visible: it analyzes historical
  network-flow datasets, it is not live monitoring, and predictions are
  investigation signals, not confirmed attacks.
- Never hardcode secrets. Use .env and reference variable names only.

## Workflow
1. Make the change.
2. Self-review: run the app, test the flows, read your own diff, and
   look for bugs, UI inconsistencies, and half-finished work.
3. Fix everything you find.
4. Report: what changed, what you tested, what you fixed in
   self-review, and what needs my decision.
5. Stop and wait for my approval before the next task.