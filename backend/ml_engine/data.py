"""Read bounded CSV files and validate tabular data."""

import csv
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .errors import DatasetValidationError


@dataclass(frozen=True)
class DatasetLimits:
    """Configurable limits for the first version of the engine."""

    max_file_bytes: int = 10 * 1024 * 1024
    max_rows: int = 50_000
    max_columns: int = 100

    def __post_init__(self):
        for value in (self.max_file_bytes, self.max_rows, self.max_columns):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("Dataset limits must be positive integers.")


DEFAULT_LIMITS = DatasetLimits()


def _validate_csv_layout(text: str, limits: DatasetLimits) -> None:
    """Check original headers before pandas automatically renames duplicates."""

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader, None)
        if not header or any(not name.strip() for name in header):
            raise DatasetValidationError("The first CSV row must contain column names.")
        if len(set(header)) != len(header):
            raise DatasetValidationError("The CSV contains duplicate column names.")
        if len(header) < 2:
            raise DatasetValidationError(
                "A feature and a target column are required; use a comma delimiter."
            )
        if len(header) > limits.max_columns:
            raise DatasetValidationError(
                f"At most {limits.max_columns} columns are allowed."
            )

        rows_count = 0
        for row in reader:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if len(row) != len(header):
                raise DatasetValidationError(
                    f"Row {reader.line_num} has a different number of values than the header."
                )
            rows_count += 1
            if rows_count > limits.max_rows:
                raise DatasetValidationError(
                    f"At most {limits.max_rows} data rows are allowed."
                )
    except csv.Error as error:
        raise DatasetValidationError(
            "The CSV contains invalid quotes or rows."
        ) from error


def validate_dataset(
    data: pd.DataFrame,
    target_column: str,
    *,
    limits: DatasetLimits = DEFAULT_LIMITS,
) -> None:
    """Validate a table without changing it; training checks task-specific rules."""

    if not isinstance(data, pd.DataFrame):
        raise DatasetValidationError("Data must be a pandas DataFrame.")
    if data.empty:
        raise DatasetValidationError("The dataset is empty.")
    if len(data) > limits.max_rows or len(data.columns) > limits.max_columns:
        raise DatasetValidationError("The dataset exceeds row or column limits.")
    if data.columns.has_duplicates:
        raise DatasetValidationError("The dataset contains duplicate column names.")
    if any(not isinstance(name, str) or not name.strip() for name in data.columns):
        raise DatasetValidationError("Every column must have a non-empty string name.")
    if not isinstance(target_column, str) or target_column not in data.columns:
        raise DatasetValidationError(f"Target column '{target_column}' was not found.")
    if len(data.columns) < 2:
        raise DatasetValidationError(
            "At least one feature column is required besides the target."
        )

    target = data[target_column]
    if target.isna().any() or target.astype("string").str.strip().eq("").any():
        raise DatasetValidationError("The target column contains missing values.")
    if any(pd.api.types.is_complex_dtype(dtype) for dtype in data.dtypes):
        raise DatasetValidationError("Complex numbers are not supported.")

    numeric = data.select_dtypes(include="number").to_numpy(
        dtype=float, na_value=np.nan
    )
    if np.isinf(numeric).any():
        raise DatasetValidationError("Numeric columns contain infinite values.")


def load_csv(
    path: str | Path,
    target_column: str,
    *,
    limits: DatasetLimits = DEFAULT_LIMITS,
) -> pd.DataFrame:
    """Read a UTF-8 CSV with a header row and comma delimiter."""

    try:
        with Path(path).open("rb") as source:
            content = source.read(limits.max_file_bytes + 1)
    except OSError as error:
        raise DatasetValidationError("Failed to open the dataset file.") from error

    if len(content) > limits.max_file_bytes:
        raise DatasetValidationError(
            f"The CSV exceeds the limit of {limits.max_file_bytes} bytes."
        )
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DatasetValidationError("The CSV must use UTF-8 encoding.") from error

    _validate_csv_layout(text, limits)
    try:
        data = pd.read_csv(io.StringIO(text), low_memory=False)
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise DatasetValidationError("Failed to read CSV content.") from error

    validate_dataset(data, target_column, limits=limits)
    return data
