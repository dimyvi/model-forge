"""Validation metrics and model selection rules."""

import math

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from .errors import TrainingError

SELECTION_METRICS = {"classification": "f1_macro", "regression": "mae"}


def calculate_metrics(task: str, actual, predicted) -> dict[str, float]:
    """Return finite floats suitable for JSONField and API responses."""
    if task == "classification":
        metrics = {
            "accuracy": float(accuracy_score(actual, predicted)),
            "f1_macro": float(
                f1_score(actual, predicted, average="macro", zero_division=0)
            ),
        }
    elif task == "regression":
        metrics = {
            "mae": float(mean_absolute_error(actual, predicted)),
            "rmse": math.sqrt(float(mean_squared_error(actual, predicted))),
            "r2": float(r2_score(actual, predicted)),
        }
    else:
        raise TrainingError("Metrics are not yet defined for this task.")
    if not all(math.isfinite(value) for value in metrics.values()):
        raise TrainingError("Failed to calculate finite metric values.")
    return metrics


def selection_score(task: str, metrics: dict[str, float]) -> float:
    """Return a score to maximize: F1 macro or negative MAE."""
    if task == "classification":
        return metrics[SELECTION_METRICS[task]]
    if task == "regression":
        return -metrics[SELECTION_METRICS[task]]
    raise TrainingError("A selection rule is not yet defined for this task.")
