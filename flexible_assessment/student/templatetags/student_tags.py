from django import template
from django.utils import timezone
from flexible_assessment.models import Assessment

register = template.Library()


@register.simple_tag()
def not_open(course):
    if course:
        if course.close == None:
            return True
        open = course.open
        close = course.close
        now = timezone.now()
        return now > close or now < open
    else:
        return False


@register.simple_tag()
def before_deadline(course):
    if course:
        if course.open == None:
            return True
        open = course.open
        now = timezone.now()
        return now < open
    else:
        return True


@register.simple_tag()
def get_default_min_max(id):
    assessment = Assessment.objects.filter(pk=id).first()
    return (assessment.default, assessment.min, assessment.max)


@register.simple_tag()
def is_any_flex_none(flexes):
    return any(f.flex is None for f in flexes)


@register.simple_tag()
def not_flexible(default_min_max):
    return default_min_max[1] == default_min_max[2]
