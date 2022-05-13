from django.apps import AppConfig
from django.db.models.signals import post_migrate


class FlexConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'flex'

    def ready(self):
        from .utils import create_groups
        post_migrate.connect(create_groups, sender=self)
