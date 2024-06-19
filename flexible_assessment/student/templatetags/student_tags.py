from django import template
from django.utils import timezone
from flexible_assessment.models import Assessment
from flexible_assessment.models import FlexAssessment

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
def after_deadline(course):
    if course:
        if course.close == None:
            return False
        close = course.close
        now = timezone.now()
        return now > close
    else:
        return False


@register.simple_tag()
def get_default_min_max(id):
    assessment = Assessment.objects.filter(pk=id).first()
    return (assessment.default, assessment.min, assessment.max)


@register.simple_tag()
def is_any_flex_outside_bounds(flexes):
    for f in flexes:
        if f.flex == None:
            continue
        flex_max = f.assessment.max
        flex_min = f.assessment.min
        if (f.flex > flex_max) or (f.flex < flex_min):
            return True
    return False


@register.simple_tag()
def is_any_flex_overriden(flexes):
    for f in flexes:
        if f.flex == None:
            continue
        if f.override:
            return True
    return False


@register.simple_tag()
def is_any_flex_none(flexes):
    return any(f.flex is None for f in flexes)


@register.simple_tag()
def not_flexible(default_min_max):
    return default_min_max[1] == default_min_max[2]


@register.simple_tag(takes_context=True)
def get_flex(context, id):
    user_id = context["user"]
    assessment = Assessment.objects.get(pk=id)
    flex_assessment = assessment.flexassessment_set.filter(
        user__user_id=user_id
    ).first()
    return flex_assessment.flex


@register.simple_tag()
def is_flex_outside_bounds(curr_flex, id):
    assessment = Assessment.objects.get(pk=id)
    if curr_flex == None:
        return False
    return (curr_flex > assessment.max) or (curr_flex < assessment.min)
