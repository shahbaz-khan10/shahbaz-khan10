from django.apps import AppConfig


class MastersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "masters"
    label = "masters"
    verbose_name = "Business Master Data"