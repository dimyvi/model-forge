"""JSON-in/JSON-out adapter for an isolated training subprocess.

The Django worker supplies local paths and metadata. This module has no Django
imports and publishes no database records or public download links.
"""

import json
import logging
import sys
from pathlib import Path

from .artifacts import save_model
from .data import load_csv
from .errors import MLEngineError
from .training import train_experiment

logger = logging.getLogger(__name__)


def run_training(config: dict) -> list[dict]:
    data = load_csv(config["dataset_path"], config["target_column"])
    results = train_experiment(
        data, config["target_column"], config["task"], config["algorithms"]
    )
    output = Path(config["output_directory"])
    summaries = []
    for result in results:
        filename = f"{result.algorithm}.joblib"
        metadata = {
            **config.get("metadata", {}),
            "task": config["task"],
            "target_column": config["target_column"],
            "feature_columns": data.drop(
                columns=config["target_column"]
            ).columns.tolist(),
            "algorithm": result.algorithm,
            "metrics": result.metrics,
            "is_best": result.is_best,
            "validation_size": 0.25,
            "random_state": 42,
            "rows_count": len(data),
        }
        save_model(result.model, output / filename, metadata=metadata)
        summaries.append(
            {
                "algorithm": result.algorithm,
                "metrics": result.metrics,
                "is_best": result.is_best,
                "filename": filename,
            }
        )
    return summaries


def main() -> int:
    try:
        results = run_training(json.load(sys.stdin))
    except MLEngineError as error:
        json.dump({"error": str(error)}, sys.stdout)
        return 1
    except Exception:
        logger.exception("Unexpected training subprocess failure")
        json.dump(
            {"error": "Training failed unexpectedly. Check the worker logs."},
            sys.stdout,
        )
        return 1
    json.dump({"results": results}, sys.stdout, allow_nan=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
