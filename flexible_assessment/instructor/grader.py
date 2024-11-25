from flexible_assessment.models import UserProfile, Roles
from decimal import Decimal, ROUND_HALF_UP


def round_half_up(value, digits=2):
    if value is None:
        return None
    """Rounds a float to the specified number of digits using ROUND_HALF_UP"""
    d = Decimal(str(value))  # Convert to Decimal
    return d.quantize(Decimal(10) ** -digits, rounding=ROUND_HALF_UP)


from decimal import Decimal


def get_default_total(groups, student):
    """Calculates default total grade for student using assignment groups"""
    student_id = student.user_id
    student_id_str = str(student_id)
    scores = []
    weights = []

    for assessment in groups.values():
        grades = assessment["grade_list"]["grades"]
        for curr_id, score in grades:
            if student_id_str == curr_id:
                if score is not None:
                    scores.append(Decimal(score))
                    weights.append(assessment["group_weight"])
                break

    # Convert weights to Decimal to avoid type mismatch
    score_weight = zip(scores, [Decimal(w) for w in weights])
    overall = Decimal(0)

    for score, weight in score_weight:
        overall += score * weight / Decimal(100)

    # Sum of weights also needs to be Decimal to avoid type mismatch
    total_weight = sum(Decimal(w) for w in weights)
    overall = overall / total_weight * Decimal(100) if total_weight != 0 else Decimal(0)

    # return overall

    # return round_half_up(overall, 3)
    return round_half_up(overall, 2)


# def get_default_total(groups, student):
#     """Calculates default total grade for student using assignment groups

#     Parameters
#     ----------
#     groups : dict
#         Assignment groups retrieved from Canvas API
#     student : UserProfile
#         Student object

#     Returns
#     -------
#     float
#         Default final grade for student
#     """

#     student_id = student.user_id
#     student_id_str = str(student_id)
#     scores = []
#     weights = []
#     for assessment in groups.values():
#         grades = assessment["grade_list"]["grades"]
#         for curr_id, score in grades:
#             if student_id_str == curr_id:
#                 if score is not None:
#                     scores.append(score)
#                     weights.append(assessment["group_weight"])
#                 break

#     score_weight = zip(scores, weights)
#     overall = 0

#     for score, weight in score_weight:
#         overall += score * weight / 100
#     overall = overall / sum(weights) * 100.0 if sum(weights) != 0.0 else 0.0

#     return round(overall, 2)


def valid_flex(student, course):
    null_flex_assessments = student.flexassessment_set.filter(
        assessment__course=course, flex__isnull=True
    )
    flex_assessments_with_flex = student.flexassessment_set.filter(
        assessment__course=course, flex__isnull=False
    )
    flex_sum = sum([fa.flex for fa in flex_assessments_with_flex])

    return (not null_flex_assessments) and (flex_sum == 100)


# def get_override_total(groups, student, course):
#     """Calculates override grade for student using assignment groups
#     and applying flex allocations. If any flex assessment is null or
#     do not all sum to 100%, then None is returned.

#     Parameters
#     ----------
#     groups : dict
#         Assignment groups retrieved from Canvas API
#     student : UserProfile
#         Student object
#     course : Course
#         Course object

#     Returns
#     -------
#     Union[float, None]
#         Override final grade for student or None if
#         student does not have a valid flex allocation
#     """

#     if not valid_flex(student, course):
#         return None

#     scores = []
#     flex_set = []
#     assessments = course.assessment_set.all()
#     for assessment in assessments:
#         flex = assessment.flexassessment_set.filter(user=student).first().flex
#         score = get_score(groups, assessment.group, student)

#         if score is not None:
#             scores.append(score)
#             flex_set.append(float(flex))

#     score_weight = zip(scores, flex_set)
#     overall = 0

#     for score, weight in score_weight:
#         overall += score * weight / 100

#     overall = overall / sum(flex_set) * 100.0 if sum(flex_set) != 0.0 else 0.0

#     return round(overall, 2)


def get_override_total(groups, student, course):
    """Calculates override grade for student using assignment groups and flex allocations"""
    if not valid_flex(student, course):
        return None

    scores = []
    flex_set = []
    assessments = course.assessment_set.all()

    for assessment in assessments:
        # Ensure that flex is a Decimal for consistent precision
        flex = Decimal(assessment.flexassessment_set.filter(user=student).first().flex)
        score = get_score(groups, assessment.group, student)

        if score is not None:
            scores.append(Decimal(score))  # Ensure score is Decimal
            flex_set.append(flex)  # Use Decimal directly

    score_weight = zip(scores, flex_set)
    overall = Decimal(0)

    # Use Decimal for all calculations here
    for score, weight in score_weight:
        overall += (score * weight) / Decimal(100)

    # Ensure the final division uses Decimal for precision
    total_flex = sum(flex_set)
    if total_flex != Decimal(0):
        overall = (overall / total_flex) * Decimal(100)
    else:
        overall = Decimal(0)

    print(f"printing before the rounding {overall}")
    # Use custom rounding function that works with Decimal
    # return overall
    # return round_half_up(overall, 3)
    return round_half_up(overall, 2)


def get_averages(groups, course):
    """Calculates the average override grade, default grade,
    and difference for all students in a course

    Parameters
    ----------
    groups : dict
        Assignment groups retrieved from Canvas API
    course : Course
        Course object

    Returns
    -------
    averages : list
        List of average override grade, average default grade,
        and average difference
    """

    students = UserProfile.objects.filter(
        usercourse__role=Roles.STUDENT, usercourse__course=course
    )

    overrides = []
    defaults = []
    diffs = []

    for student in students:
        default_total = get_default_total(groups, student)
        defaults.append(default_total)

        override = get_override_total(groups, student, course)
        if override is not None:
            overrides.append(override)
            diffs.append(override - default_total)
        else:
            overrides.append(default_total)
            diffs.append(0)

    averages = []
    for curr_list in [overrides, defaults, diffs]:
        averages.append(
            round_half_up(sum(curr_list) / len(curr_list), 2)
            if len(curr_list) != 0
            else 0
        )

    return averages


def get_group_weight(groups, id):
    """Gets Canvas assignment group weight"""

    try:
        return round(groups[str(id)]["group_weight"], 2)
    except Exception:
        return ""


def get_score(groups, group_id, student):
    """Gets student score in assignment group"""

    student_id = student.user_id
    group_id_str = str(group_id)
    student_id_str = str(student_id)
    grades = groups[group_id_str]["grade_list"]["grades"]
    for curr_id, score in grades:
        if student_id_str == curr_id:
            return score
    return None
