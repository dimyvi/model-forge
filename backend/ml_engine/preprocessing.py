"""Build preprocessing transformations fitted by the training pipeline."""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from .errors import DatasetValidationError


def _normalize_categories(values):
    """Convert categories to strings and missing or blank values to np.nan."""
    strings = pd.DataFrame(values).astype("string")
    strings = strings.replace(r"^\s*$", pd.NA, regex=True)
    return strings.to_numpy(dtype=object, na_value=np.nan)


def build_preprocessor(features: pd.DataFrame) -> ColumnTransformer:
    """Create an unfitted preprocessor without modifying input data."""
    if not isinstance(features, pd.DataFrame) or features.empty:
        raise DatasetValidationError(
            "Preprocessing requires a non-empty feature table."
        )
    numeric_columns = features.select_dtypes(include="number").columns.tolist()
    categorical_columns = [
        name for name in features.columns if name not in numeric_columns
    ]
    transformers = []
    if numeric_columns:
        numeric = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("scaler", StandardScaler()),
            ]
        )
        transformers.append(("numeric", numeric, numeric_columns))
    if categorical_columns:
        categorical = Pipeline(
            [
                (
                    "normalize",
                    FunctionTransformer(
                        _normalize_categories, feature_names_out="one-to-one"
                    ),
                ),
                (
                    "imputer",
                    SimpleImputer(
                        strategy="constant",
                        fill_value="__missing__",
                        keep_empty_features=True,
                    ),
                ),
                ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ]
        )
        transformers.append(("categorical", categorical, categorical_columns))
    return ColumnTransformer(transformers, remainder="drop")
