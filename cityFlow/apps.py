from django.apps import AppConfig


class CityflowConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cityFlow"

    def ready(self):
        import cityFlow.signals  # noqa: F401