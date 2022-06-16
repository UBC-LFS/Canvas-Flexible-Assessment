from django import template
from django.utils import timezone
from flexible_assessment.models import Assessment

register = template.Library()


@register.simple_tag()
def not_open(course):
    if course:
        open = course.open
        close = course.close
        now = timezone.now()
        return now > close or now < open
    else:
        return False


@register.simple_tag()
def get_default_min_max(id):
    assessment = Assessment.objects.filter(pk=id).first()
    return (assessment.default, assessment.min, assessment.max)
