"""Validate the original FraudShield dataset without exporting row-level data."""

import argparse
from collections import Counter
import csv
from datetime import date, datetime
from hashlib import file_digest
from io import TextIOWrapper
import json
from pathlib import Path
import re
import sys
from typing import BinaryIO, TextIO
from zipfile import BadZipFile, ZipFile


MEMBERS = ("fraudTrain.csv", "fraudTest.csv")
SCHEMA = {
    "": "export_index",
    "trans_date_trans_time": "timestamp",
    "cc_num": "card_identifier",
    "merchant": "text",
    "category": "text",
    "amt": "amount",
    "first": "text",
    "last": "text",
    "gender": "text",
    "street": "text",
    "city": "text",
    "state": "text",
    "zip": "postal_code",
    "lat": "latitude",
    "long": "longitude",
    "city_pop": "nonnegative_integer",
    "job": "text",
    "dob": "date",
    "trans_num": "transaction_id",
    "unix_time": "nonnegative_integer",
    "merch_lat": "latitude",
    "merch_long": "longitude",
    "is_fraud": "binary_label",
}
TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}")
BIRTH_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
TRANSACTION_ID = re.compile(r"[0-9a-fA-F]{32}")
AMOUNT = re.compile(r"[0-9]+(?:\.[0-9]{1,2})?")
COORDINATE = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
EPOCH = datetime(1970, 1, 1)


class DatasetError(ValueError):
    """A dataset contract failure whose message contains no row values."""


def parse_value(kind: str, value: str) -> str | datetime | int | None:
    """Validate a populated value and return data needed for aggregate checks."""
    if kind == "timestamp" and TIMESTAMP.fullmatch(value):
        return datetime.fromisoformat(value)
    if kind == "date" and BIRTH_DATE.fullmatch(value):
        date.fromisoformat(value)
        return None
    if kind == "transaction_id" and TRANSACTION_ID.fullmatch(value):
        return int(value, 16)
    if kind in ("export_index", "nonnegative_integer") and value.isascii() and value.isdecimal():
        return int(value)
    if kind == "card_identifier" and value.isascii() and value.isdecimal() and len(value) <= 19:
        return None
    if kind == "postal_code" and value.isascii() and value.isdecimal() and len(value) <= 5:
        return None
    if kind == "amount" and AMOUNT.fullmatch(value):
        return None
    if kind in ("latitude", "longitude") and COORDINATE.fullmatch(value):
        limit = 90 if kind == "latitude" else 180
        if -limit <= float(value) <= limit:
            return None
    if kind == "binary_label" and value in ("0", "1"):
        return value
    if kind == "text":
        return None
    raise ValueError


def validate_csv(stream: TextIO, member: str, earlier_ids: set[int]) -> tuple[dict, set[int]]:
    reader = csv.reader(stream, strict=True)
    if next(reader, None) != list(SCHEMA):
        raise DatasetError(f"{member} has an unexpected header.")

    missing = Counter(dict.fromkeys((name or "(unnamed export index)" for name in SCHEMA), 0))
    invalid = missing.copy()
    labels = Counter({"0": 0, "1": 0})
    ids: set[int] = set()
    first = last = previous = None
    min_offset = max_offset = None
    rows = malformed = duplicates = overlap = out_of_order = 0
    max_backward_step = 0

    for row in reader:
        rows += 1
        if len(row) != len(SCHEMA):
            malformed += 1
            continue

        parsed = {}
        for (column, kind), raw in zip(SCHEMA.items(), row, strict=True):
            value = raw.strip()
            if not value:
                missing[column or "(unnamed export index)"] += 1
                continue
            try:
                converted = parse_value(kind, value)
                if converted is not None:
                    parsed[column] = converted
            except (ValueError, OverflowError):
                invalid[column or "(unnamed export index)"] += 1

        label = parsed.get("is_fraud")
        if label is not None:
            labels[label] += 1

        transaction_id = parsed.get("trans_num")
        if transaction_id is not None:
            if transaction_id in ids:
                duplicates += 1
            else:
                ids.add(transaction_id)
                if transaction_id in earlier_ids:
                    overlap += 1

        timestamp = parsed.get("trans_date_trans_time")
        if timestamp is not None:
            first = timestamp if first is None else min(first, timestamp)
            last = timestamp if last is None else max(last, timestamp)
            if previous is not None and timestamp < previous:
                out_of_order += 1
                max_backward_step = max(max_backward_step, int((previous - timestamp).total_seconds()))
            previous = timestamp
            unix_time = parsed.get("unix_time")
            if unix_time is not None:
                offset = unix_time - int((timestamp - EPOCH).total_seconds())
                min_offset = offset if min_offset is None else min(min_offset, offset)
                max_offset = offset if max_offset is None else max(max_offset, offset)

    return {
        "rows": rows,
        "malformed_rows": malformed,
        "missing_by_column": dict(missing),
        "invalid_by_column": dict(invalid),
        "label_counts": dict(labels),
        "duplicate_transaction_id_rows": duplicates,
        "unique_transaction_ids_in_earlier_file": overlap,
        "timestamp_min": first.isoformat(sep=" ") if first is not None else None,
        "timestamp_max": last.isoformat(sep=" ") if last is not None else None,
        "out_of_order_rows": out_of_order,
        "max_backward_step_seconds": max_backward_step,
        "unix_minus_naive_timestamp_seconds": {"min": min_offset, "max": max_offset},
    }, ids


def validate_archive(path: Path) -> dict:
    with path.open("rb") as file:
        return validate_archive_stream(file)


def validate_archive_stream(file: BinaryIO) -> dict:
    """Validate a seekable ZIP stream from the beginning."""
    splits = {}
    train_ids: set[int] = set()
    file.seek(0)
    sha256 = file_digest(file, "sha256").hexdigest()
    file.seek(0)
    with ZipFile(file) as archive:
        if sorted(archive.namelist()) != sorted(MEMBERS):
            raise DatasetError("Expected one fraudTrain.csv and one fraudTest.csv in the ZIP.")
        for member in MEMBERS:
            with archive.open(member) as raw, TextIOWrapper(
                raw, encoding="utf-8-sig", newline=""
            ) as stream:
                metrics, ids = validate_csv(stream, member, train_ids)
            splits[member] = metrics
            if member == MEMBERS[0]:
                train_ids = ids

    train_end = splits[MEMBERS[0]]["timestamp_max"]
    test_start = splits[MEMBERS[1]]["timestamp_min"]
    chronological = bool(train_end and test_start and train_end < test_start)
    passed = chronological and all(
        metrics["rows"] > 0
        and all(metrics["label_counts"].values())
        and not metrics["malformed_rows"]
        and not any(metrics["missing_by_column"].values())
        and not any(metrics["invalid_by_column"].values())
        and not metrics["duplicate_transaction_id_rows"]
        and not metrics["unique_transaction_ids_in_earlier_file"]
        for metrics in splits.values()
    )
    warnings = []
    for member, metrics in splits.items():
        if metrics["out_of_order_rows"]:
            warnings.append(f"{member} requires chronological sorting before time-dependent processing.")
        offset = metrics["unix_minus_naive_timestamp_seconds"]
        if offset["min"] not in (None, 0) or offset["max"] not in (None, 0):
            warnings.append(f"{member} has a difference between unix_time and the calendar timestamp.")
    return {
        "archive_sha256": sha256,
        "observed_schema": [{"column": name, "type": kind} for name, kind in SCHEMA.items()],
        "train_ends_before_test": chronological,
        "passed": passed,
        "warnings": warnings,
        "files": splits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Path to the original Kaggle ZIP")
    args = parser.parse_args()
    try:
        report = validate_archive(args.archive)
    except DatasetError as error:
        print(f"Dataset validation failed: {error}", file=sys.stderr)
        return 2
    except (OSError, BadZipFile, csv.Error, UnicodeError, RuntimeError, NotImplementedError):
        print("Dataset validation failed: could not read the original ZIP or CSV.", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
