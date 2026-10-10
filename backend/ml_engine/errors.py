"""Domain errors handled by the worker and API."""


class MLEngineError(ValueError):
    """Base ML engine error."""


class DatasetValidationError(MLEngineError):
    """The dataset is unsuitable for training."""


class AlgorithmValidationError(MLEngineError):
    """Unknown task or unsuitable set of algorithms."""


class TrainingError(MLEngineError):
    """Invalid training parameters or a training failure."""


class ArtifactError(MLEngineError):
    """A trained model could not be saved."""
