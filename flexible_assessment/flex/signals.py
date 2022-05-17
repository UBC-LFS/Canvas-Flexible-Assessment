from django.db.models.signals import post_save
from django.dispatch import receiver

from .utils import add_permissions
from .models import FlexAssessment, UserCourse, UserProfile, Roles


@receiver(post_save, sender=UserProfile)
def add_perms(sender, instance, created, **kwargs):
    if created:
        add_permissions()


@receiver(post_save, sender=UserCourse)
def add_flex_assessments(sender, instance, created, **kwargs):
    user = instance.user
    if user.role == Roles.STUDENT:
        assessment_courses = instance.course.assessmentcourse_set.all()
        assessments = [
            assessment_course.assessment for assessment_course in assessment_courses]
        flex_assessments = [
            FlexAssessment(
                user=user,
                assessment=assessment) for assessment in assessments]
        FlexAssessment.objects.bulk_create(flex_assessments)
