from django import template

register = template.Library()


@register.filter
def assessment_filter(flex_set, assessment_id):
    return flex_set.get(assessment__id=assessment_id)


@register.filter
def comment_filter(comment_set, course_id):
    return comment_set.get(course__id=course_id)
