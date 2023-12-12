from django import template
from flexible_assessment.models import Assessment, Roles
import json

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
    return str(value) + "%" if value is not None else None


@register.simple_tag()
def get_response_rate(course):
    user_courses = course.usercourse_set.filter(role=Roles.STUDENT)
    students = [user_course.user for user_course in user_courses]
    valid_num = sum([grader.valid_flex(student, course) for student in students])
    if len(students) > 0:
        percentage = round(valid_num / len(students) * 100, 2)
    else:
        percentage = 0
    return valid_num, len(students), percentage


@register.simple_tag()
def get_number_responses(course):
    user_courses = course.usercourse_set.filter(role=Roles.STUDENT)
    students = [user_course.user for user_course in user_courses]
    valid_num = sum([grader.valid_flex(student, course) for student in students])
    return valid_num


@register.simple_tag()
def get_average_allocations(course):
    assessments = course.assessment_set.all()
    series = []
    for assessment in assessments.order_by("order"):
        fas = assessment.flexassessment_set.exclude(flex__isnull=True)
        if len(fas) > 0:
            student_average = round(sum([fa.flex for fa in fas]) / len(fas), 2)
        else:
            student_average = assessment.default
        series.append(
            {
                "name": assessment.title,
                "data": [float(assessment.default), float(student_average)],
            }
        )

    return series


@register.simple_tag()
def get_allocations(course):
    """Return a list with default allocations, allocations chosen, then all students"""
    assessments = course.assessment_set.all()
    data = {
        "defaults": [],
        "chose": [],
        "all": [],
    }  # If none chosen, have chose be empty
    for index, assessment in enumerate(assessments.order_by("order")):
        # colors = ["#7D3AC1", "#AF4BCE", "#DB4CB2", "#EB548C", "#EA7369", "#F0A58F", "#FDA58F", "#FCEAE6"]
        # colors = ['#002145', '#003B6F', '#00509E', '#0065CE', '#007BFF', '#4D8AFF', '#7FAFFF', '#B3D4FF', '#E6F0FF', '#FDB813']
        colors = [
            "#002145",
            "#003B6F",
            "#00509E",
            "#0065CE",
            "#007BFF",
            "#4D8AFF",
            "#7FAFFF",
            "#B3D4FF",
            "#E6F0FF",
            "#FDB813",
            "#FF69B4",
            "#FFDAB9",
            "#00CED1",
            "#FF6347",
            "#BA55D3",
        ]
        color = (
            "#C5C6D0"
            if assessment.min == assessment.max
            else colors[index % len(colors)]
        )

        all_flexes = assessment.flexassessment_set.all()
        fas_chosen = all_flexes.exclude(flex__isnull=True)
        if len(fas_chosen) > 0:
            student_average = round(
                sum([fa.flex for fa in fas_chosen]) / len(fas_chosen), 2
            )
            data["chose"].append(
                {"name": assessment.title, "y": float(student_average), "color": color}
            )
            all_students = round(
                sum(
                    [
                        fa.flex if fa.flex is not None else assessment.default
                        for fa in all_flexes
                    ]
                )
                / len(fas_chosen),
                2,
            )
            data["all"].append(
                {"name": assessment.title, "y": float(all_students), "color": color}
            )

        else:
            # If none chosen, then it all students is just the default
            data["all"].append(
                {
                    "name": assessment.title,
                    "y": float(assessment.default),
                    "color": color,
                }
            )

        data["defaults"].append(
            {"name": assessment.title, "y": float(assessment.default), "color": color}
        )

    return json.dumps(data)


@register.simple_tag()
def get_flex_difference(course):
    """For each assessment in the course, return the difference between the default flex and the student choices average"""
    assessments = course.assessment_set.all()
    data = {}
    for assessment in assessments.order_by("order"):
        fas_chosen = assessment.flexassessment_set.exclude(flex__isnull=True)
        if len(fas_chosen) > 0:
            difference = round(
                sum([fa.flex - assessment.default for fa in fas_chosen])
                / len(fas_chosen),
                2,
            )
            data[assessment.title] = float(difference)
        else:
            data[assessment.title] = 0

    return json.dumps(data)


@register.simple_tag()
def get_score(groups, group_id, student):
    score = grader.get_score(groups, group_id, student)
    return str(score) + "%" if score is not None else None


@register.simple_tag()
def get_student_grades(groups, student, course):
    default = grader.get_default_total(groups, student)
    default_str = str(default) + "%"
    override = grader.get_override_total(groups, student, course)
    if override is not None:
        override_str = str(override) + "%"
        diff = round(override - default, 2)
        prefix = "+" if diff > 0 else ""
        diff_str = prefix + str(diff) + "%"
        return ("overriden", override_str, default_str, diff_str)
    else:
        return ("used-default", default_str, default_str, "0.00%")


@register.simple_tag()
def get_default_min_max(id):
    assessment = Assessment.objects.filter(pk=id).first()
    return (assessment.default, assessment.min, assessment.max)


@register.simple_tag()
def not_flexible(default_min_max):
    return default_min_max[1] == default_min_max[2]


@register.simple_tag()
def get_group_weight(groups, id):
    return grader.get_group_weight(groups, id)


@register.simple_tag()
def get_group_weight_percentage(groups, id):
    percentage = grader.get_group_weight(groups, id)
    if percentage is not None:
        return f"{percentage:.2f}%"
    else:
        return ""


@register.simple_tag()
def get_averages_str(groups, course):
    averages = grader.get_averages(groups, course)
    overall_avg, default_avg, diff_avg = averages[0], averages[1], averages[2]
    overall_str = str(overall_avg) + "%"
    default_str = str(default_avg) + "%"

    prefix = "+" if diff_avg > 0 else ""
    diff_str = prefix + str(diff_avg) + "%"
    return (overall_str, default_str, diff_str)
