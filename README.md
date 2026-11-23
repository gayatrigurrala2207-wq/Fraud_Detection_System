# FraudShield

FraudShield is a local-first portfolio project for scoring financial transactions, explaining fraud risk, and supporting analyst investigations. From the original Kaggle dataset it builds point-in-time features, compares seven models chronologically, deploys a LightGBM model with SHAP explanations, and replays the 555,719 held-out transactions through the scorer. The React analyst UI covers all nine required views (FR-06 to FR-12) with live data: overview metrics, a live feed, a case workspace, analytics, model reporting, drift monitoring, replay controls with a manual simulator, health, and settings.

## Run the website

You need two terminals, both opened at the repository root. Prerequisites: [uv](https://docs.astral.sh/uv/getting-started/installation/), [Node.js](https://nodejs.org/) 20.19 or newer, and the Kaggle ZIP at `backend/data/raw/fraud-detection.zip` (see [Validate the original dataset](#validate-the-original-dataset)).

**One-time data build** (about 12 minutes on a laptop CPU). It trains the model, writes reports to `backend/data/reports/` and the model to `backend/data/models/`, loads the replay database at `backend/data/processed/fraudshield.sqlite`, and scores the first 2,000 transactions. Rerunning it replaces the database, including cases and notes.

```sh
cd backend
uv sync --locked
uv run --locked python -m scripts.build_all
```

**Terminal 1 — backend API** (http://localhost:8000, interactive docs at http://localhost:8000/docs):

```sh
cd backend
uv run --locked python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend UI** (http://localhost:5173):

```sh
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. **On first visit you create the administrator account**; after that the site shows a sign-in page. The administrator adds other people under **Users** with one of three roles:

| Role | Can |
| --- | --- |
| Viewer | Read every page. |
| Analyst | Viewer, plus label, annotate, resolve, and reopen cases; start, pause, and fast-forward the replay; use the simulator. |
| Admin | Analyst, plus manage users (create, change role, disable, reset password) and reset the replay. |

Passwords are stored as salted scrypt hashes. Sessions last 12 hours in an HttpOnly, SameSite=Lax cookie; tokens are stored server-side only as hashes. Five failed sign-ins for a username lock it for 15 minutes. Accounts live in `backend/data/auth/users.sqlite`, separate from the replay database, so `build_all` never deletes them. Every case action is recorded under the signed-in username. If you forget the only admin password, stop the backend and delete `backend/data/auth/users.sqlite` to run first-time setup again. Behind HTTPS, set `FRAUDSHIELD_COOKIE_SECURE=true`.

While the backend runs, its replay worker scores 5 transactions per second (change the speed, pause, fast-forward, or reset on **Replay & Simulator**). Flagged transactions open cases you can label, annotate, and resolve. If a page says it cannot reach the backend, check that terminal 1 is still running. The frontend dev server forwards every `/api` request to port 8000.

| Endpoint | Requirement | Returns |
| --- | --- | --- |
| `GET /api/auth/status`, `POST /api/auth/setup`, `/login`, `/logout`, `/password`, `GET /api/auth/me` | Access | Public sign-in and first-run setup; everything below requires a signed-in user. |
| `GET/POST /api/users`, `PATCH /api/users/{id}`, `POST /api/users/{id}/password` | Access | Admin-only user management. |
| `GET /api/overview` | FR-06 | Processed, flagged, high-risk, potential fraud value, predicted vs confirmed outcomes, latency, with definitions. |
| `GET /api/transactions` | FR-07 | Live feed with `risk`, `status`, `source`, `q`, and `min_amount` filters. |
| `GET /api/cases`, `GET /api/cases/{id}` | FR-08 | Case list; case evidence, SHAP explanation, behavioral anomalies, masked card history, notes, audit trail. |
| `POST /api/cases/{id}/label`, `/notes`, `/resolve`, `/reopen` | FR-08 | Analyst actions, attributed to the signed-in user and audited. |
| `GET /api/analytics` | FR-09 | Fraud patterns from publisher labels plus the live score distribution. |
| `GET /api/models` | FR-10 | Model comparison, test metrics, PR/ROC curves, confusion matrix, feature importance, latency. |
| `GET /api/monitoring` | FR-10 | PSI drift vs the validation window, confirmed-label performance, experiment runs. |
| `GET/POST /api/replay`, `POST /api/simulate` | FR-11 | Replay status and controls; score a manual transaction stored as simulated. |
| `GET /api/health`, `GET /api/settings` | FR-12 | Dependency status and active configuration. |
| `GET /api/dataset/validation` | FR-01 | Aggregate validation results. Never row-level data. |

Local substitutes, as allowed by decision 006: SQLite stands in for PostgreSQL, and an in-process replay worker stands in for Kafka. Behavioral features are precomputed per transaction instead of kept in Redis. System Health lists these as not configured.

## Repository layout

Open `Fraud_detection_System` directly as the folder in VS Code. Its workspace settings hide local Python environments, caches, and temporary test directories from the Explorer.

```text
Fraud_detection_System/
├── backend/                    # Python project: ML, pipelines, API, and tests
│   ├── app/                    # FastAPI analyst API
│   │   ├── main.py             # App entry point (uvicorn app.main:app); starts the replay worker
│   │   ├── auth.py             # Password hashing, sessions, roles
│   │   ├── config.py           # Environment-based settings and data locations
│   │   ├── db.py               # SQLite schema: transactions, cases, notes, audit events
│   │   ├── replay.py           # Background replay worker
│   │   ├── services.py         # Shared request dependencies (database, model, analyst)
│   │   └── routes/             # auth/users, overview, transactions, cases, insights, replay, health, settings
│   ├── ml/                     # Machine learning (imported as ml.*)
│   │   ├── preprocessing/      # Dataset validation CLI and archive loader
│   │   ├── features/           # Point-in-time feature engineering (FR-03)
│   │   ├── training/           # Model comparison, selection, and artifact writing (FR-04)
│   │   ├── evaluation/         # Metrics and cost threshold, drift (PSI), analytics aggregates
│   │   ├── inference/          # Deployed-model scoring and SHAP explanations
│   │   └── notebooks/          # Exploratory analysis (reserved)
│   ├── pipelines/              # Transaction flow
│   │   ├── producers/          # Loads held-out transactions into the replay queue
│   │   └── consumers/          # Scores queued transactions and opens cases
│   ├── data/                   # Local data, ignored by Git except placeholders
│   │   ├── raw/                # Original Kaggle ZIP, never modified
│   │   ├── reports/            # Validation, model, analytics, and run reports
│   │   ├── auth/               # User accounts and sessions (generated, kept across rebuilds)
│   │   ├── models/             # Deployed model, metadata, drift reference (generated)
│   │   └── processed/          # SQLite replay database (generated)
│   ├── scripts/                # build_all.py: one command to build all data
│   ├── tests/                  # Backend test suite (pytest)
│   ├── .env.example            # Backend environment template; copy to .env (ignored)
│   ├── .python-version         # Python 3.12 pin
│   ├── pyproject.toml          # Python manifest and pytest configuration
│   ├── uv.lock                 # Locked Python dependency versions
│   └── README.md               # Backend command reference
├── frontend/                   # React + TypeScript analyst UI (Vite, Tailwind CSS)
│   ├── src/
│   │   ├── components/         # Sidebar layout, charts (Recharts), shared UI pieces
│   │   ├── pages/              # Sign-in/setup, one page per view, case workspace, users, account
│   │   ├── auth.tsx            # Session state, sign-in, sign-out
│   │   ├── api.ts              # Typed backend client
│   │   └── main.tsx            # Entry point
│   ├── index.html
│   ├── package.json            # npm scripts and dependencies (package-lock.json pins them)
│   ├── tsconfig.json
│   └── vite.config.ts          # Dev server on 5173, proxies /api to the backend
├── infrastructure/
│   └── monitoring/             # Planned experiment tracking and drift monitoring
├── configs/
│   └── training.json           # Split date, threshold costs, risk cutoffs, seed
├── docs/                       # Requirements, architecture, and development records
├── .github/
│   └── workflows/              # CI workflows (reserved)
├── .vscode/
│   └── settings.json           # Explorer exclusions for local tooling files
├── .gitignore
├── Makefile                    # setup / test / check shortcuts (run from the root)
└── README.md
```

Local-only directories such as `backend/.venv/`, `.uv-cache/`, `.uv-python/`, and `.pytest_cache/` are ignored by Git and hidden in VS Code.

### Directory responsibilities

| Directory | Used by | Responsibility |
| --- | --- | --- |
| `backend/` | Backend | Self-contained Python project with its own manifest, lockfile, and virtual environment. |
| `backend/app/` | Backend | The analyst API service: overview, feed, cases, analytics, models, monitoring, replay, health, and settings endpoints, plus SQLite persistence. |
| `backend/ml/` | Backend | Offline modeling: dataset validation, features, training, evaluation, and the inference code the API and consumers import. |
| `backend/pipelines/` | Backend | Event streaming. Producers replay historical transactions; consumers validate, enrich, and score them. |
| `backend/data/` | Backend | Local datasets and generated reports. Contents are ignored by Git; only folder placeholders are tracked. |
| `backend/scripts/` | Backend | Backend developer and automation scripts. |
| `backend/tests/` | Backend | The pytest suite. Tests use small synthetic fixtures and need no downloaded data. |
| `frontend/` | Frontend | The analyst workspace UI. Talks to the backend only through `/api` and has its own npm toolchain. |
| `infrastructure/` | Both | Local service definitions (Docker Compose) and operational tooling such as monitoring. |
| `configs/` | Both | Versioned, non-secret configuration shared across components. Secrets belong in `.env`, never here. |
| `docs/` | Both | Requirements, architecture, roadmap, decision log, progress, and validation results. |
| `.github/` | Both | CI workflows that verify backend and frontend. |

### How the components interact

`scripts/build_all.py` reads `backend/data/raw`, computes features with `ml/features`, and trains and evaluates with `ml/training` and `ml/evaluation` using `configs/training.json`. It then has the producer in `pipelines/producers` load the held-out test file into SQLite, with card numbers replaced by keyed pseudonyms and no names, addresses, or labels stored. While the API runs, its replay worker calls the consumer in `pipelines/consumers`. The consumer scores each queued transaction with `ml/inference` and opens a case when the score meets the threshold. The UI in `frontend/` reads everything through `/api`. See [Architecture](docs/architecture.md) for the full flow.

## Local setup

Install Git and uv. The current Python commands need no environment variables or credentials. Run them in a macOS terminal or Windows PowerShell **from the `backend/` directory** (`cd backend`). On Apple Silicon, use a native arm64 terminal and uv installation. [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/)

| Command (in `backend/`) | What it does |
| --- | --- |
| `uv sync --locked` | Finds or downloads Python 3.12, creates `backend/.venv`, and installs dependencies from `uv.lock`. Fails if the manifest and lockfile disagree. |
| `uv lock --check` | Checks that the lockfile matches the dependency declarations. |
| `uv run --locked python -m pytest` | Runs the environment and dataset validation tests inside the project environment without manual activation. |
| `uv run --locked python -c "import platform; print(platform.python_version(), platform.machine())"` | Prints the interpreter version and machine architecture. Expect Python 3.12 and arm64 on a native Apple Silicon setup. |

On macOS, run `make setup`, `make test`, or `make check` from the repository root; the Makefile switches into `backend/` for you. When changing dependencies, update and review both `backend/pyproject.toml` and `backend/uv.lock`. [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)

To install Python separately, use `uv python install 3.12 --no-bin`. On Windows in a restricted shell, add `--no-registry` to skip registering the interpreter. [uv Python setup](https://docs.astral.sh/uv/guides/install-python/)

In VS Code, select `backend/.venv` as the Python interpreter after the first `uv sync`.

### Environment variables

Phase 2 needs none. When later phases add settings, copy `backend/.env.example` to `backend/.env` and fill in local values; `.env` files are ignored by Git.

### Windows with a restricted user cache

If uv cannot write to its default cache, run these commands in PowerShell **from the repository root**, then `cd backend`. They point uv at the workspace-local cache and interpreter used on the verification host.

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD '.uv-python'
```

If uv reports `invalid peer certificate: UnknownIssuer` (a network that inspects TLS traffic), also set `$env:UV_SYSTEM_CERTS = '1'` so uv trusts the Windows certificate store. Windows Application Control may block generated launchers such as `pytest.exe` and `uvicorn.exe`; the documented `python -m ...` commands avoid them.

## Testing

```sh
cd backend
uv run --locked python -m pytest
```

Tests live in `backend/tests/` and are discovered through `backend/pyproject.toml`, which also puts `backend/` on the import path so `ml.*` modules resolve from IDE test runners. Tests run with pytest's cache disabled so they can run from a workspace shared by Windows accounts.

## Validate the original dataset

Download the ZIP from the [Kaggle dataset page](https://www.kaggle.com/datasets/kartik2112/fraud-detection). A direct download is also available from the `backend/` directory:

```sh
curl --fail --location --output data/raw/fraud-detection.zip https://www.kaggle.com/api/v1/datasets/download/kartik2112/fraud-detection
```

Use `curl.exe` in Windows PowerShell. If the endpoint returns a sign-in page or challenge, use Kaggle's browser download and save the ZIP as `backend/data/raw/fraud-detection.zip`. The validator reads both CSVs from the archive.

```sh
uv run --locked python -m ml.preprocessing.validate_dataset data/raw/fraud-detection.zip
```

The command prints an aggregate JSON report and returns exit code 0 for a passing archive, 1 for failed quality checks, or 2 for an unreadable archive or schema mismatch. The report also lists time-order and timestamp-representation warnings. To keep a copy, redirect the output to `data/reports/validation.json`. Keep source files in the ignored `backend/data/` directory and avoid sharing raw rows.

Frontend checks, from `frontend/`: `npm run typecheck` checks types and `npm run build` produces a production bundle in `frontend/dist/` (ignored by Git).

## Build and deployment

For local use, run the two dev servers described in [Run the website](#run-the-website). `npm run build` creates the static frontend bundle; `npm run preview` serves it for a final check. Container startup (Docker Compose) and CI (GitHub Actions) commands will be added as those components are implemented.

## Documentation

- [Software requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Implementation roadmap](docs/roadmap.md)
- [Engineering decision log](docs/decisions.md)
- [Development progress](docs/progress.md)
- [Dataset validation results](docs/dataset-validation.md)
