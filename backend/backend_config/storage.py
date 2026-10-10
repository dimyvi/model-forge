"""Schedule independent file cleanup after database commits."""

import logging

from django.db import transaction

logger = logging.getLogger(__name__)


def delete_file_after_commit(storage, name):
    def remove_file():
        try:
            storage.delete(name)
        except Exception:
            # Keep the exact failed path in logs and continue other cleanup callbacks.
            logger.exception(
                "File cleanup failed for %s; retry deleting this file.", name
            )

    transaction.on_commit(remove_file, robust=True)
