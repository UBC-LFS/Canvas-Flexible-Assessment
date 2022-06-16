from django.apps import AppConfig
from django.db.models.signals import post_migrate


class FlexConfig(AppConfig):
    """Extends AppConfig for startup routines"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'flexible_assessment'

    def ready(self):
        """Creates groups based on models.Roles on server ready"""
        import flexible_assessment.signals
        from .utils import create_groups
        post_migrate.connect(create_groups, sender=self)
