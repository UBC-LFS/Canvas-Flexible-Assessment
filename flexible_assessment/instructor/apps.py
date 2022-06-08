from django.db.models.signals import post_migrate
from django.apps import AppConfig


class InstructorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'instructor'

    def ready(self):
        """Creates groups based on models.Roles on server ready"""
        import flexible_assessment.signals
        from flexible_assessment.utils import create_groups
        post_migrate.connect(create_groups, sender=self)