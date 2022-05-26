from django.db.models.signals import post_save
from django.dispatch import receiver

from .utils import add_permissions
from .models import FlexAssessment, UserCourse, UserProfile, Assessment, Roles


@receiver(post_save, sender=UserProfile)
def add_perms(sender, instance, created, **kwargs):
    if created:
        add_permissions()


@receiver(post_save, sender=UserCourse)
def add_flex_assessments(sender, instance, created, **kwargs):
    user = instance.user
    if user.role == Roles.STUDENT:
        assessments = instance.course.assessment_set.all()
        flex_assessments = [
            FlexAssessment(
                user=user,
                assessment=assessment) for assessment in assessments]
        FlexAssessment.objects.bulk_create(flex_assessments)


@receiver(post_save, sender=Assessment)
def update_flex_assessments(sender, instance, created, **kwargs):
    flex_assessments = list(
        filter(
            lambda fa: fa.flex is not None,
            instance.flexassessment_set.all()))
    min = instance.min
    max = instance.max
    update = False

    for flex_assessment in flex_assessments:
        if flex_assessment.flex < min or flex_assessment.flex > max:
            flex_assessment.flex = None
            update = True

    if update:
        FlexAssessment.objects.bulk_update(flex_assessments, ['flex'])
