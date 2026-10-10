from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import numpy as np
import pandas as pd

from ml_engine.data import DatasetLimits, load_csv, validate_dataset
from ml_engine.errors import DatasetValidationError


class CsvLoadingTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def csv_file(self, text):
        path = self.directory / "data.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_loads_utf8_bom_and_quoted_values(self):
        path = self.csv_file('\ufeffcity,target\n"Montréal, centre",yes\nZürich,no\n')

        data = load_csv(path, "target")

        self.assertEqual(data.columns.tolist(), ["city", "target"])
        self.assertEqual(data.loc[0, "city"], "Montréal, centre")

    def test_skips_empty_lines(self):
        data = load_csv(self.csv_file("x,target\n1,a\n\n   \n2,b\n"), "target")

        self.assertEqual(len(data), 2)

    def test_rejects_duplicate_headers_before_pandas_renames_them(self):
        with self.assertRaisesRegex(DatasetValidationError, "duplicate"):
            load_csv(self.csv_file("x,x,target\n1,2,a\n3,4,b\n"), "target")

    def test_rejects_blank_header_and_wrong_row_width(self):
        for text in (" ,target\n1,a\n", "x,y,target\n1,a\n", "x,target\n1,2,a\n"):
            with self.subTest(text=text), self.assertRaises(DatasetValidationError):
                load_csv(self.csv_file(text), "target")

    def test_rejects_empty_file_and_missing_data(self):
        for text in ("", "x,target\n"):
            with self.subTest(text=text), self.assertRaises(DatasetValidationError):
                load_csv(self.csv_file(text), "target")

    def test_rejects_invalid_quotes(self):
        with self.assertRaises(DatasetValidationError):
            load_csv(self.csv_file('x,target\n"unterminated,a\n'), "target")

    def test_rejects_non_utf8_file_and_missing_file(self):
        path = self.directory / "invalid.csv"
        path.write_bytes(b"x,target\n\xff,a\n")
        with self.assertRaisesRegex(DatasetValidationError, "UTF-8"):
            load_csv(path, "target")
        with self.assertRaisesRegex(DatasetValidationError, "open"):
            load_csv(self.directory / "missing.csv", "target")

    def test_enforces_byte_row_and_column_limits(self):
        path = self.csv_file("x,y,target\n1,2,a\n3,4,b\n")
        limits_to_test = (
            DatasetLimits(max_file_bytes=8),
            DatasetLimits(max_rows=1),
            DatasetLimits(max_columns=2),
        )
        for limits in limits_to_test:
            with self.subTest(limits=limits), self.assertRaises(DatasetValidationError):
                load_csv(path, "target", limits=limits)


class DatasetValidationTests(TestCase):
    def test_accepts_missing_features_without_changing_data(self):
        data = pd.DataFrame({"x": [1.0, np.nan], "target": ["a", "b"]})
        before = data.copy(deep=True)

        validate_dataset(data, "target")

        pd.testing.assert_frame_equal(data, before)

    def test_rejects_empty_non_table_or_target_only_input(self):
        for data in ([], pd.DataFrame(), pd.DataFrame({"target": [1, 2]})):
            with (
                self.subTest(data=repr(data)),
                self.assertRaises(DatasetValidationError),
            ):
                validate_dataset(data, "target")

    def test_rejects_missing_target_and_missing_target_values(self):
        for target in (["a", None], ["a", "  "], ["a", pd.NA]):
            with self.subTest(target=target), self.assertRaises(DatasetValidationError):
                validate_dataset(
                    pd.DataFrame({"x": [1, 2], "target": target}), "target"
                )
        with self.assertRaises(DatasetValidationError):
            validate_dataset(pd.DataFrame({"x": [1, 2], "target": [3, 4]}), "missing")

    def test_rejects_nonfinite_and_complex_numbers(self):
        for values in ([1, np.inf], [1, -np.inf], [1 + 2j, 3 + 4j]):
            with self.subTest(values=values), self.assertRaises(DatasetValidationError):
                validate_dataset(
                    pd.DataFrame({"x": values, "target": [1, 2]}), "target"
                )

    def test_rejects_invalid_column_names_and_duplicates(self):
        for columns in (["x", "x"], ["", "target"], [1, "target"]):
            data = pd.DataFrame([[1, 2], [3, 4]], columns=columns)
            with (
                self.subTest(columns=columns),
                self.assertRaises(DatasetValidationError),
            ):
                validate_dataset(data, "target")

    def test_direct_tables_respect_limits(self):
        data = pd.DataFrame({"x": [1, 2], "target": [3, 4]})
        with self.assertRaises(DatasetValidationError):
            validate_dataset(data, "target", limits=DatasetLimits(max_rows=1))

    def test_limits_require_positive_integers(self):
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                DatasetLimits(max_rows=value)
