"""Verify the local development environment and repository configuration."""

import sys
import tomllib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_python_matches_project_pin() -> None:
    expected_version = (ROOT / ".python-version").read_text().strip()
    assert f"{sys.version_info.major}.{sys.version_info.minor}" == expected_version


def test_pytest_runs_in_an_isolated_environment() -> None:
    assert sys.prefix != sys.base_prefix
    assert Path(pytest.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())


def test_project_and_pytest_are_locked() -> None:
    with (ROOT / "pyproject.toml").open("rb") as manifest:
        project = tomllib.load(manifest)["project"]
    assert project["name"] == "fraudshield"
    with (ROOT / "uv.lock").open("rb") as lockfile:
        packages = tomllib.load(lockfile)["package"]
    assert {"fraudshield", "pytest"} <= {package["name"] for package in packages}
