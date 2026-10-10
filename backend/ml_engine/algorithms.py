"""Algorithm registry with identifiers, labels, and fresh estimator factories."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression

from .errors import AlgorithmValidationError


@dataclass(frozen=True)
class AlgorithmDefinition:
    label: str
    factory: Callable[[int], BaseEstimator]


def _logistic_regression(seed: int) -> BaseEstimator:
    return LogisticRegression(max_iter=1000, random_state=seed)


def _random_forest_classifier(seed: int) -> BaseEstimator:
    return RandomForestClassifier(
        n_estimators=100, max_depth=12, n_jobs=1, random_state=seed
    )


def _linear_regression(seed: int) -> BaseEstimator:
    return LinearRegression()


def _random_forest_regressor(seed: int) -> BaseEstimator:
    return RandomForestRegressor(
        n_estimators=100, max_depth=12, n_jobs=1, random_state=seed
    )


ALGORITHM_REGISTRY = {
    "classification": {
        "logistic_regression": AlgorithmDefinition(
            "Logistic Regression", _logistic_regression
        ),
        "random_forest": AlgorithmDefinition(
            "Random Forest", _random_forest_classifier
        ),
    },
    "regression": {
        "linear_regression": AlgorithmDefinition(
            "Linear Regression", _linear_regression
        ),
        "random_forest": AlgorithmDefinition("Random Forest", _random_forest_regressor),
    },
}


def available_algorithms(task: str) -> dict[str, str]:
    """Return algorithm identifiers and labels for the API."""

    if not isinstance(task, str) or task not in ALGORITHM_REGISTRY:
        raise AlgorithmValidationError(
            "Supported tasks are classification and regression."
        )
    return {
        name: definition.label for name, definition in ALGORITHM_REGISTRY[task].items()
    }


def validate_algorithms(task: str, selected: Sequence[str]) -> None:
    """Validate identifiers without constructing or fitting estimators."""
    available = available_algorithms(task)
    if (
        isinstance(selected, (str, bytes))
        or not isinstance(selected, Sequence)
        or not selected
    ):
        raise AlgorithmValidationError("Provide a non-empty list of algorithms.")
    if any(not isinstance(name, str) for name in selected):
        raise AlgorithmValidationError("Algorithm identifiers must be strings.")
    if len(selected) != len(set(selected)):
        raise AlgorithmValidationError("Algorithms must not be repeated.")
    unknown = [name for name in selected if name not in available]
    if unknown:
        raise AlgorithmValidationError(
            f"Not available for task {task}: {', '.join(unknown)}."
        )


def create_algorithms(
    task: str, selected: Sequence[str], *, random_state: int = 42
) -> dict[str, BaseEstimator]:
    """Validate the selection and create fresh estimators for this run."""
    validate_algorithms(task, selected)
    return {
        name: ALGORITHM_REGISTRY[task][name].factory(random_state) for name in selected
    }
