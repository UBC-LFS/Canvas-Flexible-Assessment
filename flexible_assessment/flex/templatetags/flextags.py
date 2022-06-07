from django import template
from datetime import datetime
from zoneinfo import ZoneInfo

from flex.models import Assessment, Roles, UserProfile

register = template.Library()


@register.filter
def assessment_filter(flex_set, assessment_id):
    return flex_set.get(assessment__id=assessment_id)


@register.filter
def comment_filter(comment_set, course_id):
    return comment_set.get(course__id=course_id)


@register.simple_tag(takes_context=True)
def not_open(context):
    course = context["course"]
    if course:
        open = course.open
        close = course.close
        now = datetime.now(ZoneInfo('America/Vancouver'))
        return now > close or now < open
    else:
        return False


@register.simple_tag()
def get_score(groups, group_id, student):
    student_id = student.user_id
    group_id_str = str(group_id)
    student_id_str = str(student_id)
    grades = groups[group_id_str]['grade_list']['grades']
    for curr_id, score in grades:
        if student_id_str == curr_id:
            return score


def get_default_total(groups, student):
    student_id = student.user_id
    student_id_str = str(student_id)
    scores = []
    weights = []
    for assessment in groups.values():
        grades = assessment['grade_list']['grades']
        for curr_id, score in grades:
            if student_id_str == curr_id:
                if score is not None:
                    scores.append(score)
                    weights.append(assessment['group_weight'])
                break

    score_weight = zip(scores, weights)
    overall = 0

    for score, weight in score_weight:
        overall += score * weight / 100
    overall = overall / sum(weights) * 100

    return round(overall, 2)


def get_override_total(groups, student, course):
    null_flex_assessments = student.flexassessment_set.filter(
        assessment__course=course, flex__isnull=True)
    flex_assessments_with_flex = student.flexassessment_set.filter(
        assessment__course=course, flex__isnull=False)
    flex_sum = sum([fa.flex for fa in flex_assessments_with_flex])
    if any(null_flex_assessments) or flex_sum != 100:
        return ''

    student_id = student.user_id
    student_id_str = str(student_id)
    scores = []
    flex_set = []
    assessments = course.assessment_set.all()
    for assessment in assessments:
        flex = assessment.flexassessment_set.filter(
            user_id=student_id).first().flex
        group_id_str = str(assessment.group.id)
        group_assessment = groups[group_id_str]
        grades = group_assessment['grade_list']['grades']
        for curr_id, score in grades:
            if student_id_str == curr_id:
                if score is not None:
                    scores.append(score)
                    if flex is not None:
                        flex_set.append(float(flex))

    score_weight = zip(scores, flex_set)
    overall = 0

    for score, weight in score_weight:
        overall += score * weight / 100
    overall = overall / sum(flex_set) * 100

    return round(overall, 2)


@register.simple_tag()
def get_override_total_str(groups, student, course):
    overall = get_override_total(groups, student, course)
    return str(overall) + '%' if overall is not '' else 'N/A'


@register.simple_tag()
def get_default_total_str(groups, student):
    overall = get_default_total(groups, student)
    return str(overall) + '%'


@register.simple_tag()
def get_default_min_max(id):
    assessment = Assessment.objects.filter(pk=id).first()
    return (assessment.default, assessment.min, assessment.max)


@register.simple_tag()
def get_group_weight(groups, id):
    try:
        return groups[str(id)]['group_weight']
    except BaseException:
        return ''


def get_averages(groups, course):
    students = UserProfile.objects.filter(role=Roles.STUDENT, usercourse__course=course)
    overrides = [get_override_total(groups, student, course)
                 for student in students]
    defaults = [get_default_total(groups, student) for student in students]
    override_default = zip(overrides, defaults)
    diffs = []
    for override, default_total in override_default:
        if override is not '':
            diffs.append(override - default_total)
    overrides_valid = list(filter(lambda ov: ov is not '', overrides))

    averages = []
    for curr_list in [overrides_valid, defaults, diffs]:
        averages.append(
            round(
                sum(curr_list) /
                len(curr_list),
                2) if len(curr_list) != 0 else 0)

    return averages


@register.simple_tag()
def get_averages_str(groups, course):
    averages = get_averages(groups, course)
    overall_avg, default_avg, diff_avg = averages[0], averages[1], averages[2]
    overall_str = str(overall_avg) + '%'
    default_str = str(default_avg) + '%'

    prefix = '+' if diff_avg > 0 else ''
    diff_str = prefix + str(diff_avg) + '%'
    return (overall_str, default_str, diff_str)
