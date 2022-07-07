from flexible_assessment.models import UserProfile, Roles


def get_default_total(groups, student):
    """Calculates default total grade for student using assignment groups

    Parameters
    ----------
    groups : dict
        Assignment groups retrieved from Canvas API
    student : UserProfile
        Student object
    """

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
    overall = overall / sum(weights) * 100 if sum(weights) != 0 else 0

    return round(overall, 2)


def valid_flex(student, course):
    null_flex_assessments = student.flexassessment_set.filter(
        assessment__course=course, flex__isnull=True)
    flex_assessments_with_flex = student.flexassessment_set.filter(
        assessment__course=course, flex__isnull=False)
    flex_sum = sum([fa.flex for fa in flex_assessments_with_flex])

    return (not null_flex_assessments) and (flex_sum == 100)


def get_override_total(groups, student, course):
    """Calculates override grade for student using assignment groups
    and applying flex allocations. If any flex assessment is null or
    do not all sum to 100%, then an empty string ('') is returned.

    Parameters
    ----------
    groups : dict
        Assignment groups retrieved from Canvas API
    student : UserProfile
        Student object
    course : Course
        Course object
    """

    if not valid_flex(student, course):
        return None

    scores = []
    flex_set = []
    assessments = course.assessment_set.all()
    for assessment in assessments:
        flex = assessment.flexassessment_set.filter(user=student)\
            .first()\
            .flex
        score = get_score(groups, assessment.group.id, student)

        if score is not None:
            scores.append(score)
            flex_set.append(float(flex))

    score_weight = zip(scores, flex_set)
    overall = 0

    for score, weight in score_weight:
        overall += score * weight / 100

    overall = overall / sum(flex_set) * 100 if sum(flex_set) != 0 else 0

    return round(overall, 2)


def get_averages(groups, course):
    """Calculates the average override grade, default grade,
    and difference for all students in a course

    Parameters
    ----------
    groups : dict
        Assignment groups retrieved from Canvas API
    course : Course
        Course object
    """

    students = UserProfile.objects.filter(
        role=Roles.STUDENT, usercourse__course=course)

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
            round(
                sum(curr_list) /
                len(curr_list),
                2) if len(curr_list) != 0 else 0)

    return averages


def get_group_weight(groups, id):
    try:
        return int(round(groups[str(id)]['group_weight']))
    except BaseException:
        return ''


def get_score(groups, group_id, student):
    """Gets student score in assignment group"""

    student_id = student.user_id
    group_id_str = str(group_id)
    student_id_str = str(student_id)
    grades = groups[group_id_str]['grade_list']['grades']
    for curr_id, score in grades:
        if student_id_str == curr_id:
            return score
    return None
