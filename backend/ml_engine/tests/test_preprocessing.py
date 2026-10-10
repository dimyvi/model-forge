from unittest import TestCase

import numpy as np
import pandas as pd

from ml_engine.errors import DatasetValidationError
from ml_engine.preprocessing import build_preprocessor


def dense(values):
    return values.toarray() if hasattr(values, "toarray") else values


class PreprocessingTests(TestCase):
    def test_handles_numeric_and_pandas_string_missing_values(self):
        features = pd.DataFrame(
            {
                "age": [20.0, np.nan, 40.0],
                "city": pd.Series(["Montréal", pd.NA, "Zürich"], dtype="string"),
            }
        )
        before = features.copy(deep=True)

        transformed = dense(build_preprocessor(features).fit_transform(features))

        self.assertEqual(transformed.shape[0], 3)
        self.assertTrue(np.isfinite(transformed).all())
        pd.testing.assert_frame_equal(features, before)

    def test_unseen_categories_and_empty_strings_can_be_transformed(self):
        features = pd.DataFrame({"city": ["Montréal", "Zürich", None]})
        preprocessor = build_preprocessor(features).fit(features)

        transformed = dense(
            preprocessor.transform(pd.DataFrame({"city": ["Tokyo", " "]}))
        )

        self.assertEqual(transformed.shape[0], 2)
        self.assertTrue(np.isfinite(transformed).all())

    def test_all_missing_columns_are_preserved(self):
        features = pd.DataFrame(
            {
                "number": [np.nan, np.nan],
                "category": pd.Series([pd.NA, pd.NA], dtype="string"),
            }
        )
        preprocessor = build_preprocessor(features).fit(features)

        transformed = dense(
            preprocessor.transform(pd.DataFrame({"number": [5.0], "category": ["new"]}))
        )

        self.assertEqual(transformed.shape, (1, 2))
        self.assertTrue(np.isfinite(transformed).all())

    def test_supports_numeric_only_data(self):
        features = pd.DataFrame({"value": [1, 2, 3]})
        preprocessor = build_preprocessor(features).fit(features)

        transformed = dense(preprocessor.transform(features))

        self.assertEqual(transformed.shape, (3, 1))
        self.assertAlmostEqual(float(transformed.mean()), 0.0)

    def test_new_preprocessor_is_unfitted(self):
        preprocessor = build_preprocessor(pd.DataFrame({"value": [1, 2]}))

        self.assertFalse(hasattr(preprocessor, "transformers_"))

    def test_rejects_missing_features(self):
        for features in (pd.DataFrame(), pd.DataFrame(index=[0, 1]), []):
            with (
                self.subTest(features=repr(features)),
                self.assertRaises(DatasetValidationError),
            ):
                build_preprocessor(features)
