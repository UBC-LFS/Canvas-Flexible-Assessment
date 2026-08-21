from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import FlexAssessment, UserCourse, Roles


@receiver(post_save, sender=UserCourse)
def add_flex_assessments(sender, instance, created, raw=False, **kwargs):
    """Creates flex assessments for new user linked to course"""

    if raw or not created or instance.role != Roles.STUDENT:
        return

    assessments = instance.course.assessment_set.all()
    flex_assessments = [
        FlexAssessment(user=instance.user, assessment=assessment)
        for assessment in assessments
    ]
    FlexAssessment.objects.bulk_create(flex_assessments)
