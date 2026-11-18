# FraudShield

FraudShield is a local-first portfolio project for scoring financial transactions, explaining fraud risk, and supporting analyst investigations. The current implementation validates the original transaction dataset in a reproducible Python environment.

## Local setup

Install Git and uv. The current Python commands need no environment variables or credentials. The commands below work in a macOS terminal or Windows PowerShell from the repository root. On Apple Silicon, use a native arm64 terminal and uv installation. [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/)

| Command | What it does |
| --- | --- |
| `uv sync --locked` | Finds or downloads Python 3.12, creates `.venv`, and installs dependencies from `uv.lock`. Fails if the manifest and lockfile disagree. |
| `uv lock --check` | Checks that the lockfile matches the dependency declarations. |
| `uv run --locked python -m pytest` | Runs the environment and dataset validation tests inside the project environment without manual activation. |
| `uv run --locked python -c "import platform; print(platform.python_version(), platform.machine())"` | Prints the interpreter version and machine architecture. Expect Python 3.12 and arm64 on a native Apple Silicon setup. |

On macOS, `make setup` runs the sync and `make check` runs the lockfile check and tests. When changing dependencies, update and review both `pyproject.toml` and `uv.lock`. [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)

To install Python separately, use `uv python install 3.12 --no-bin`. On Windows in a restricted shell, add `--no-registry` to skip registering the interpreter. [uv Python setup](https://docs.astral.sh/uv/guides/install-python/)

Phase 1 smoke tests run with pytest's cache disabled so they can run from a workspace shared by Windows accounts.

### Windows with a restricted user cache

If uv cannot write to its default cache, run these commands in PowerShell from the project root. They point uv at the workspace-local cache and interpreter used on the verification host.

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD '.uv-python'
```

## Validate the original dataset

Download the ZIP from the [Kaggle dataset page](https://www.kaggle.com/datasets/kartik2112/fraud-detection). A direct download is also available from the project root:

```sh
curl --fail --location --output data/fraud-detection.zip https://www.kaggle.com/api/v1/datasets/download/kartik2112/fraud-detection
```

Use `curl.exe` in Windows PowerShell. If the endpoint returns a sign-in page or challenge, use Kaggle's browser download and save the ZIP as `data/fraud-detection.zip`. The validator reads both CSVs from the archive.

```sh
uv run --locked python -m ml.preprocessing.validate_dataset data/fraud-detection.zip
```

The command prints an aggregate JSON report and returns exit code 0 for a passing archive, 1 for failed quality checks, or 2 for an unreadable archive or schema mismatch. The report also lists time-order and timestamp-representation warnings. Keep the source files in the ignored `data/` directory and avoid sharing raw rows.

## Repository layout

Open `Fraud_detection_System` directly as the folder in VS Code. Its workspace settings hide local Python environments, caches, and temporary test directories from the Explorer.

```text
Fraud_detection_System/
├── apps/
│   ├── backend/           # Planned analyst API
│   └── frontend/          # Planned analyst UI
├── ml/
│   ├── preprocessing/    # Dataset validation CLI
│   ├── notebooks/         # Planned exploratory analysis
│   ├── features/          # Planned feature engineering
│   ├── training/          # Planned model training
│   ├── evaluation/        # Planned model evaluation
│   └── inference/         # Planned scoring
├── pipelines/
│   ├── producers/         # Planned transaction replay
│   └── consumers/         # Planned event processing
├── infrastructure/
│   └── monitoring/        # Planned experiment tracking and drift monitoring
├── configs/               # Reserved for shared versioned configuration
├── data/                  # Ignored local dataset and validation output
├── docs/                  # Requirements, architecture, and development records
├── scripts/               # Reserved for developer automation
├── tests/                 # Environment and dataset validation tests
├── .github/workflows/      # Reserved for CI
├── .vscode/settings.json   # Explorer exclusions for local tooling files
├── .env.example
├── .gitignore
├── .python-version
├── Makefile
├── pyproject.toml
├── uv.lock
└── README.md
```

## Development and deployment

Run the dataset validation command above from the project root to exercise the current entry point. It reads the ZIP in `data/` and prints aggregate JSON. The pytest suite uses small synthetic archives and can run without the Kaggle download.

In the planned application, the replay producer will publish transactions for the consumer to validate and score. The backend will expose scores and investigation data to the frontend. Infrastructure will host local services and monitoring. Application build, service startup, and deployment commands are pending those implementations.

- [Software requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Implementation roadmap](docs/roadmap.md)
- [Engineering decision log](docs/decisions.md)
- [Development progress](docs/progress.md)
- [Dataset validation results](docs/dataset-validation.md)
