"""Save a fitted pipeline and its metadata as a .joblib artifact."""

import json
import os
import platform
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.exceptions import NotFittedError
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from .errors import ArtifactError

ARTIFACT_SCHEMA_VERSION = 1


def save_model(
    model: Pipeline,
    destination: str | Path,
    *,
    metadata: Mapping | None = None,
) -> Path:
    """Atomically save a pipeline with JSON-compatible experiment metadata."""

    if not isinstance(model, Pipeline):
        raise ArtifactError(
            "Saving requires a pipeline containing preprocessing and an estimator."
        )
    try:
        check_is_fitted(model)
    except NotFittedError as error:
        raise ArtifactError("The model must be fitted before saving.") from error

    try:
        experiment_metadata = json.loads(
            json.dumps(dict(metadata or {}), allow_nan=False)
        )
    except (TypeError, ValueError) as error:
        raise ArtifactError("Model metadata must be JSON-compatible.") from error

    destination = Path(destination)
    if destination.suffix.lower() != ".joblib":
        raise ArtifactError("The model file must have a .joblib extension.")

    payload = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "pipeline": model,
        "metadata": {
            "created_at": datetime.now(UTC).isoformat(),
            "library_versions": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "scipy": scipy.__version__,
                "scikit-learn": sklearn.__version__,
                "joblib": joblib.__version__,
            },
            "experiment": experiment_metadata,
        },
    }

    temporary_path = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        joblib.dump(payload, temporary_path, compress=3)
        os.replace(temporary_path, destination)
    except Exception as error:
        raise ArtifactError("Failed to save the model file.") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return destination
