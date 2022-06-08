from django import template
from datetime import datetime
from zoneinfo import ZoneInfo
from flexible_assessment.models import Assessment

register = template.Library()

@register.simple_tag()
def not_open(course):
    if course:
        open = course.open
        close = course.close
        now = datetime.now(ZoneInfo('America/Vancouver'))
        return now > close or now < open
    else:
        return False


@register.simple_tag()
def get_default_min_max(id):
    assessment = Assessment.objects.filter(pk=id).first()
    return (assessment.default, assessment.min, assessment.max)
