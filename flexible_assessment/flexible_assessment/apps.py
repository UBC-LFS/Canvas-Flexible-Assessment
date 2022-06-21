from django.apps import AppConfig


class FlexConfig(AppConfig):
    """Extends AppConfig for startup routines"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'flexible_assessment'
