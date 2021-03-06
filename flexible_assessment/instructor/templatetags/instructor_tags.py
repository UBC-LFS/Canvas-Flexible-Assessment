from django import template
from flexible_assessment.models import Assessment, Roles

from .. import grader

register = template.Library()


@register.filter
def assessment_filter(flex_set, assessment_id):
    return flex_set.get(assessment__id=assessment_id)


@register.filter
def comment_filter(comment_set, course_id):
    return comment_set.get(course__id=course_id)


@register.filter
def to_str(value):
    return str(value)+'%' if value is not None else None


@register.simple_tag()
def get_response_rate(course):
    user_courses = course.usercourse_set.filter(
            user__role=Roles.STUDENT)
    students = [user_course.user for user_course in user_courses]
    valid_num = sum([grader.valid_flex(student, course)
                    for student in students])
    if len(students) > 0:
        percentage = round(valid_num/len(students)*100, 2)
    else:
        percentage = 0
    return ('{} / {}'.format(valid_num, len(students)),
            '{}%'.format(percentage))


@register.simple_tag()
def get_average_allocations(course):
    assessments = course.assessment_set.all()
    series = []
    for assessment in assessments:
        fas = assessment.flexassessment_set.exclude(flex__isnull=True)
        if len(fas) > 0:
            student_average = round(sum([fa.flex for fa in fas])/len(fas), 2)
        else:
            student_average = assessment.default
        series.append({
            'name': assessment.title,
            'data': [assessment.default, student_average]
        })

    return series


@register.simple_tag()
def get_score(groups, group_id, student):
    score = grader.get_score(groups, group_id, student)
    return str(score)+'%' if score is not None else None


@register.simple_tag()
def get_student_grades(groups, student, course):
    default = grader.get_default_total(groups, student)
    default_str = str(default) + '%'
    override = grader.get_override_total(groups, student, course)
    if override is not None:
        override_str = str(override) + '%'
        diff = round(override - default, 2)
        prefix = '+' if diff > 0 else ''
        diff_str = prefix + str(diff) + '%'
        return ('overriden', override_str, default_str, diff_str)
    else:
        return ('used-default', default_str, default_str, '0.00%')


@register.simple_tag()
def get_default_min_max(id):
    assessment = Assessment.objects.filter(pk=id).first()
    return (assessment.default, assessment.min, assessment.max)


@register.simple_tag()
def get_group_weight(groups, id):
    return grader.get_group_weight(groups, id)


@register.simple_tag()
def get_averages_str(groups, course):
    averages = grader.get_averages(groups, course)
    overall_avg, default_avg, diff_avg = averages[0], averages[1], averages[2]
    overall_str = str(overall_avg) + '%'
    default_str = str(default_avg) + '%'

    prefix = '+' if diff_avg > 0 else ''
    diff_str = prefix + str(diff_avg) + '%'
    return (overall_str, default_str, diff_str)
