import logging
from django.forms import ValidationError

from instructor.canvas_api import FlexCanvas

import flexible_assessment.models as models

logger = logging.getLogger(__name__)


def update_students(request, course):
    """Updates student list in database to match that of the Canvas course."""
    students_canvas = FlexCanvas(request)\
        .get_course(course.id)\
        .get_users(enrollment_type='student')
    students_canvas = list(students_canvas)
    students_db = models.UserProfile.objects. \
        filter(usercourse__role=models.Roles.STUDENT,
               usercourse__course=course)

#    log_extra = {'course': str(course),
#                 'user': request.session['display_name']}

    students_canvas_ids = [student.__getattribute__(
        'id') for student in students_canvas]
    students_db_ids = [student.user_id for student in students_db]

    students_to_add = list(
        filter(
            lambda student: student.__getattribute__('id')
            not in students_db_ids,
            students_canvas))
    students_to_delete = students_db.exclude(user_id__in=students_canvas_ids)

    for student in students_to_add:
        canvas_fields = {}
        canvas_fields['user_id'] = student.__getattribute__('id')
        canvas_fields['login_id'] = student.__getattribute__('sis_user_id')
        canvas_fields['user_display_name'] = student.__getattribute__('name')
        canvas_fields['course_id'] = course.id
        canvas_fields['course_name'] = course.title
        set_user_course(canvas_fields, models.Roles.STUDENT)

#        logger.info('User added %s',
#                    canvas_fields['user_display_name'], extra=log_extra)

    if students_to_delete:
#        logger.info('Users deleted: %s',
#                    ', '.join(students_to_delete.values_list(
#                        'display_name', flat=True)),
#                    extra=log_extra)
        students_to_delete.delete()


def set_user_profile(user_id, login_id, display_name):
    user_set = models.UserProfile.objects.filter(pk=user_id)
    if not user_set.exists():
        user = models.UserProfile.objects.create_user(
            user_id, login_id, display_name)
    else:
        user = user_set.first()
    return user


def set_course(course_id, course_name):
    course_set = models.Course.objects.filter(pk=course_id)
    if not course_set.exists():
        logger.info("New Course Created:", extra={'course': course_name, 'user': course_id})        
        course = models.Course(id=course_id, title=course_name)
        course.save()
    else:
        course = course_set.first()
    return course


def set_user_course_enrollment(user, course, role):
    user_course_set = models.UserCourse.objects.filter(
        user_id=user.user_id, course_id=course.id)
    if not user_course_set.exists():
        user_course = models.UserCourse(user=user, course=course, role=role)
        user_course.save()


def set_user_comment(user, course):
    if not user.usercomment_set.filter(course__id=course.id).exists():
        user_comment = models.UserComment(user=user, course=course)
        user_comment.save()


def set_user_course(canvas_fields, role):
    """Creates relevant database objects if they do not exist for a user."""

    user_id = canvas_fields['user_id']
    login_id = canvas_fields['login_id']
    display_name = canvas_fields['user_display_name']
    course_id = canvas_fields['course_id']
    course_name = canvas_fields['course_name']

    user = set_user_profile(user_id, login_id, display_name)
    course = set_course(course_id, course_name)

    set_user_course_enrollment(user, course, role)
    if role == models.Roles.STUDENT:
        set_user_comment(user, course)


def find_invalid_flex_ranges(assessments, total_min, total_max):
    """ 
    Given a list of assessments (dictionary that contains title, min, max, form) and total_min, total_max
    which are the sums of all the assessments min/max values, add form.errors if invalid. 
    Assessments are invalid if the min value does not allow the total to reach 100. Or
    if the max value causes the total to always go above 100
    """
    for assessment in assessments:
        if not ('min' in assessment and 'max' in assessment):
            continue

        current_min = assessment['min']
        current_max = assessment['max']

        total_with_current_min = total_max - current_max + current_min 
        if total_with_current_min < 100:
            assessment['form'].add_error(
                'min',
                ValidationError(f'Not possible for students to select. Please increase to {current_min + 100 - total_with_current_min} or increase the total max of other assessments to {100 - current_min}')
            )
        
        total_with_current_max = total_min - current_min + current_max
        if total_with_current_max > 100:
            assessment['form'].add_error(
                'max',
                ValidationError(f'Not possible for students to select. Please decrease to {current_max - (total_with_current_max - 100)} or decrease the total min of other assessments to {100 - current_max}')
            )