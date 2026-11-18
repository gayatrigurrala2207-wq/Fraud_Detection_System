# FraudShield backend

The Python side of FraudShield: dataset validation and ML code (`ml/`), streaming pipelines (`pipelines/`), the planned FastAPI service (`app/`), and their tests. Run every command below from this `backend/` directory.

| Command | What it does |
| --- | --- |
| `uv sync --locked` | Creates `backend/.venv` with Python 3.12 and the locked dependencies. |
| `uv lock --check` | Checks that `uv.lock` matches `pyproject.toml`. |
| `uv run --locked python -m pytest` | Runs the test suite. |
| `uv run --locked python -m uvicorn app.main:app --reload --port 8000` | Starts the API on http://localhost:8000 (docs at `/docs`). |
| `uv run --locked python -m ml.preprocessing.validate_dataset data/raw/fraud-detection.zip` | Validates the original Kaggle archive and prints an aggregate JSON report. |

See the [project README](../README.md) for the full layout, dataset download, and setup notes.
