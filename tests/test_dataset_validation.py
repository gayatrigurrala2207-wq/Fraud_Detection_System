"""Regression tests for the original dataset contract using small fixture rows."""

import csv
from io import BytesIO, StringIO
from zipfile import ZipFile

import pytest

from ml.preprocessing.validate_dataset import (
    MEMBERS,
    SCHEMA,
    DatasetError,
    validate_archive_stream,
)


def make_row(index, timestamp, transaction_id, label, **overrides):
    row = dict.fromkeys(SCHEMA, "example")
    row.update(
        {
            "": str(index),
            "trans_date_trans_time": timestamp,
            "cc_num": "000000000001",
            "amt": "10.25",
            "zip": "00101",
            "lat": "45.5",
            "long": "-90",
            "city_pop": "0",
            "dob": "1980-01-01",
            "trans_num": f"{transaction_id:032x}",
            "unix_time": "1600000000",
            "merch_lat": "-90",
            "merch_long": "180",
            "is_fraud": str(label),
        }
    )
    row.update(overrides)
    return [row[column] for column in SCHEMA]


def make_archive(train, test, train_header=SCHEMA):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, rows, header in zip(MEMBERS, (train, test), (train_header, SCHEMA), strict=True):
            stream = StringIO(newline="")
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows)
            archive.writestr(name, stream.getvalue())
    return buffer


def test_valid_archive_reports_aggregate_results():
    train = [make_row(i, f"2020-01-01 00:00:0{i}", i, i) for i in range(2)]
    test = [make_row(i, f"2020-01-02 00:00:0{i}", i + 2, i) for i in range(2)]
    with make_archive(train, test) as archive:
        report = validate_archive_stream(archive)

    assert report["passed"] is True
    assert report["files"][MEMBERS[0]]["label_counts"] == {"0": 1, "1": 1}
    assert "000000000001" not in str(report)


def test_flags_invalid_values_duplicates_and_overlapping_splits():
    train = [
        make_row(0, "2020-01-02 00:00:00", 10, 0),
        make_row(1, "2020-01-01 00:00:00", 10, 1, lat="91", category=" "),
        ["short row"],
    ]
    test = [make_row(0, "2020-01-02 00:00:00", 10, 2)]
    with make_archive(train, test) as archive:
        report = validate_archive_stream(archive)
    train_report, test_report = (report["files"][name] for name in MEMBERS)

    assert report["passed"] is False
    assert report["train_ends_before_test"] is False
    assert train_report["malformed_rows"] == 1
    assert train_report["duplicate_transaction_id_rows"] == 1
    assert train_report["out_of_order_rows"] == 1
    assert train_report["invalid_by_column"]["lat"] == 1
    assert train_report["missing_by_column"]["category"] == 1
    assert test_report["unique_transaction_ids_in_earlier_file"] == 1
    assert test_report["invalid_by_column"]["is_fraud"] == 1


def test_unexpected_header_error_does_not_echo_input():
    with make_archive([], [], train_header=["private value"]) as archive:
        with pytest.raises(DatasetError, match=r"^fraudTrain\.csv has an unexpected header\.$"):
            validate_archive_stream(archive)


def test_source_time_anomalies_warn_without_invalidating_split():
    train = [
        make_row(0, "2020-01-01 00:00:01", 10, 0),
        make_row(1, "2020-01-01 00:00:00", 11, 1),
    ]
    test = [make_row(i, f"2020-01-02 00:00:0{i}", i + 12, i) for i in range(2)]
    with make_archive(train, test) as archive:
        report = validate_archive_stream(archive)

    assert report["passed"] is True
    assert report["files"][MEMBERS[0]]["max_backward_step_seconds"] == 1
    assert report["warnings"] == [
        "fraudTrain.csv requires chronological sorting before time-dependent processing.",
        "fraudTrain.csv has a difference between unix_time and the calendar timestamp.",
        "fraudTest.csv has a difference between unix_time and the calendar timestamp.",
    ]
