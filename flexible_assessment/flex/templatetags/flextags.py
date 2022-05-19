from django import template
from datetime import datetime
from zoneinfo import ZoneInfo

register = template.Library()


@register.filter
def assessment_filter(flex_set, assessment_id):
    return flex_set.get(assessment__id=assessment_id)


@register.filter
def comment_filter(comment_set, course_id):
    return comment_set.get(course__id=course_id)


@register.simple_tag(takes_context=True)
def past_deadline(context):
    course = context["course"]
    print(course.deadline)
    if course:
        deadline = course.deadline
        return datetime.now(ZoneInfo('America/Vancouver')) > deadline
    else:
        return False
