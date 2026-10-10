"""Train and compare algorithms using the same validation split."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil
from numbers import Real

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.utils.multiclass import type_of_target

from .algorithms import create_algorithms
from .data import DEFAULT_LIMITS, DatasetLimits, validate_dataset
from .errors import DatasetValidationError, TrainingError
from .metrics import calculate_metrics, selection_score
from .preprocessing import build_preprocessor


@dataclass
class TrainingResult:
    """A fitted preprocessing/model pipeline and its validation metrics."""

    algorithm: str
    metrics: dict[str, float]
    model: Pipeline
    is_best: bool = False


def _validate_target(target: pd.Series, task: str) -> None:
    if task == "classification":
        try:
            target_type = type_of_target(target)
        except (TypeError, ValueError) as error:
            raise DatasetValidationError(
                "The target contains incompatible class labels."
            ) from error
        if target_type not in {"binary", "multiclass"}:
            raise DatasetValidationError(
                "Classification requires categories or integer labels."
            )
        if target.nunique() < 2:
            raise DatasetValidationError(
                "Classification requires at least two classes."
            )
        if target.value_counts().min() < 2:
            raise DatasetValidationError("Each class must contain at least two rows.")
    else:
        if not pd.api.types.is_numeric_dtype(target) or pd.api.types.is_bool_dtype(
            target
        ):
            raise DatasetValidationError("Regression requires a numeric target column.")
        if target.nunique() < 2:
            raise DatasetValidationError("Regression requires distinct target values.")


def train_experiment(
    data: pd.DataFrame,
    target_column: str,
    task: str,
    algorithm_names: Sequence[str],
    *,
    validation_size: float = 0.25,
    random_state: int = 42,
    limits: DatasetLimits = DEFAULT_LIMITS,
) -> list[TrainingResult]:
    """Train models on one split and select the best validation result.

    This function does not write to a database or filesystem. The validation
    split compares algorithms; it is not an independent final test set.
    """
    validate_dataset(data, target_column, limits=limits)
    if (
        isinstance(validation_size, bool)
        or not isinstance(validation_size, Real)
        or not 0 < validation_size < 1
    ):
        raise TrainingError("Validation size must be a number between 0 and 1.")
    if (
        isinstance(random_state, bool)
        or not isinstance(random_state, int)
        or not 0 <= random_state < 2**32
    ):
        raise TrainingError("random_state must be an integer between 0 and 2**32 - 1.")

    algorithms = create_algorithms(task, algorithm_names, random_state=random_state)
    features = data.drop(columns=[target_column])
    target = data[target_column]
    _validate_target(target, task)
    validation_rows = ceil(len(data) * validation_size)
    train_rows = len(data) - validation_rows
    minimum_rows = max(2, target.nunique()) if task == "classification" else 2
    if min(validation_rows, train_rows) < minimum_rows:
        raise DatasetValidationError(
            "Not enough rows for training and validation splits."
        )
    try:
        x_train, x_validation, y_train, y_validation = train_test_split(
            features,
            target,
            test_size=validation_size,
            random_state=random_state,
            stratify=target if task == "classification" else None,
        )
    except ValueError as error:
        raise DatasetValidationError(
            "Failed to split data into train and validation sets."
        ) from error
    if task == "classification" and (
        y_train.nunique() != target.nunique()
        or y_validation.nunique() != target.nunique()
    ):
        raise DatasetValidationError(
            "Some classes are missing from the validation split; add more rows for rare classes."
        )

    results = []
    for name, estimator in algorithms.items():
        model = Pipeline(
            [("preprocessor", build_preprocessor(x_train)), ("estimator", estimator)]
        )
        try:
            model.fit(x_train, y_train)
            predictions = model.predict(x_validation)
        except (ValueError, TypeError) as error:
            raise TrainingError(
                f"Failed to train algorithm '{name}' on the selected data."
            ) from error
        results.append(
            TrainingResult(
                algorithm=name,
                metrics=calculate_metrics(task, y_validation, predictions),
                model=model,
            )
        )

    best = max(results, key=lambda result: selection_score(task, result.metrics))
    best.is_best = True
    return results
