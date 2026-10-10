from django.apps import AppConfig


class ExperimentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "experiments"

    def ready(self):
        from . import signals  # noqa: F401
