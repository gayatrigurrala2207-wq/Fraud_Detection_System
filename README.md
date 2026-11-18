# FraudShield

FraudShield is a local-first portfolio project for scoring financial transactions, explaining fraud risk, and supporting analyst investigations. The current implementation validates the original transaction dataset (Phase 2) and runs a starter website: a FastAPI backend serving health, settings, and dataset validation results, and a React analyst UI with all nine required views. Views whose data comes from later phases show empty states until real results exist; see the [roadmap](docs/roadmap.md).

## Run the website

You need two terminals, both opened at the repository root. Prerequisites: [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Node.js](https://nodejs.org/) 20.19 or newer.

**Terminal 1 — backend API** (http://localhost:8000, interactive docs at http://localhost:8000/docs):

```sh
cd backend
uv sync --locked
uv run --locked python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend UI** (http://localhost:5173):

```sh
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The **System Health** page should list the API as OK and show the dataset validation results; the Overview shows dataset totals. If a page says it cannot reach the backend, check that terminal 1 is still running. The frontend dev server forwards every `/api` request to port 8000.

| Endpoint | Requirement | Returns |
| --- | --- | --- |
| `GET /api/health` | FR-12 | API status and the status of each dependency (dataset, model, PostgreSQL, Kafka, Redis). |
| `GET /api/dataset/validation` | FR-01 | Aggregate validation results from `backend/data/reports/validation.json`. Never row-level data. |
| `GET /api/settings` | FR-12 | Active non-secret configuration. |

## Repository layout

Open `Fraud_detection_System` directly as the folder in VS Code. Its workspace settings hide local Python environments, caches, and temporary test directories from the Explorer.

```text
Fraud_detection_System/
├── backend/                    # Python project: ML, pipelines, API, and tests
│   ├── app/                    # FastAPI analyst API
│   │   ├── main.py             # App entry point (uvicorn app.main:app)
│   │   ├── config.py           # Environment-based settings
│   │   └── routes/             # health, dataset, settings endpoints
│   ├── ml/                     # Offline machine learning (imported as ml.*)
│   │   ├── preprocessing/      # Dataset validation CLI (implemented)
│   │   ├── notebooks/          # Planned exploratory analysis
│   │   ├── features/           # Planned feature engineering
│   │   ├── training/           # Planned model training
│   │   ├── evaluation/         # Planned model evaluation
│   │   └── inference/          # Planned scoring
│   ├── pipelines/              # Streaming transaction flow
│   │   ├── producers/          # Planned transaction replay
│   │   └── consumers/          # Planned event validation and scoring
│   ├── data/                   # Local data, ignored by Git except placeholders
│   │   ├── raw/                # Original Kaggle ZIP, never modified
│   │   └── reports/            # Generated validation output
│   ├── scripts/                # Backend developer automation (reserved)
│   ├── tests/                  # Backend test suite (pytest)
│   ├── .env.example            # Backend environment template; copy to .env (ignored)
│   ├── .python-version         # Python 3.12 pin
│   ├── pyproject.toml          # Python manifest and pytest configuration
│   ├── uv.lock                 # Locked Python dependency versions
│   └── README.md               # Backend command reference
├── frontend/                   # React + TypeScript analyst UI (Vite, Tailwind CSS)
│   ├── src/
│   │   ├── components/         # Layout with the nine-view sidebar, shared UI pieces
│   │   ├── pages/              # Overview, System Health, Settings, planned-view empty state
│   │   ├── api.ts              # Typed backend client
│   │   └── main.tsx            # Entry point
│   ├── index.html
│   ├── package.json            # npm scripts and dependencies (package-lock.json pins them)
│   ├── tsconfig.json
│   └── vite.config.ts          # Dev server on 5173, proxies /api to the backend
├── infrastructure/
│   └── monitoring/             # Planned experiment tracking and drift monitoring
├── configs/                    # Shared versioned configuration (reserved)
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
| `backend/app/` | Backend | The analyst API service. Today: health, settings, and dataset validation endpoints. Later: scoring, cases, WebSockets, and persistence. |
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

In the planned application, the replay producer in `backend/pipelines/producers` publishes transactions read from `backend/data/raw`. The consumer in `backend/pipelines/consumers` validates each event, builds features with `backend/ml/features`, and scores it with `backend/ml/inference`. Scores and cases are persisted and exposed by the API in `backend/app` to the UI in `frontend/`. `infrastructure/` hosts the local services and monitoring. See [Architecture](docs/architecture.md) for the full flow.

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
