import logging
import pprint

from django.http import HttpResponseRedirect, JsonResponse, HttpResponseBadRequest, HttpResponseServerError
from django.urls import reverse
from django.views.decorators.http import require_POST
from pylti1p3.contrib.django import DjangoMessageLaunch, DjangoOIDCLogin
from pylti1p3.exception import LtiException

from . import auth, lti, models, utils

logger = logging.getLogger(__name__)

# https://github.com/dmitry-viskov/pylti1.3-django-example/blob/master/game/game/views.py
def login(request):
    try:
        tool_conf = lti.get_tool_conf()
        launch_data_storage = lti.get_launch_data_storage()

        oidc_login = DjangoOIDCLogin(
            request,
            tool_conf,
            launch_data_storage=launch_data_storage)
        target_link_uri = lti.get_launch_url(request)
        return oidc_login.enable_check_cookies().redirect(target_link_uri)
    
    except LtiException as e:
        logger.error(f"OIDC login failed with LtiException: {e}", extra={'course': f'Request: {str(request)}',
                           'user': 'No user'})
        return HttpResponseBadRequest("An error occurred during login: Likely due to a Canvas deployment ID key issue. Please contact it@landfood.ubc.ca for assistance. Please include your course code and the current time.")
    except Exception as e:
        logger.error(f"OIDC login failed with a generic Exception: {e}", extra={'course': f'Request: {str(request)}',
                           'user': 'No user'})
        return HttpResponseServerError("An error occurred during login. Please contact it@landfood.ubc.ca for assistance. Please include your course code and the current time.")

@require_POST
def launch(request):
    tool_conf = lti.get_tool_conf()
    launch_data_storage = lti.get_launch_data_storage()
    message_launch = DjangoMessageLaunch(
        request, tool_conf, launch_data_storage=launch_data_storage)
    message_launch_data = message_launch.get_launch_data()
    pprint.pprint(message_launch_data)

    canvas_fields = message_launch_data['https://purl.imsglobal.org'
                                        '/spec/lti/claim/custom']
    course_id = canvas_fields['course_id']

    if 'ISS' in canvas_fields['role']:
        utils.set_user_course(canvas_fields, models.Roles.ADMIN)
        auth.authenticate_login(request, canvas_fields)

        course = models.Course.objects.get(pk=course_id)
        logger.info('Admin login',
                    extra={'course': str(course),
                           'user': canvas_fields['user_display_name']})

        return HttpResponseRedirect(
            reverse('instructor:instructor_home',
                    kwargs={'course_id': course_id}) + '?login_redirect=True')

    elif 'TeacherEnrollment' in canvas_fields['role']:
        utils.set_user_course(canvas_fields, models.Roles.TEACHER)
        auth.authenticate_login(request, canvas_fields)

        course = models.Course.objects.get(pk=course_id)
        logger.info('Instructor login',
                    extra={'course': str(course),
                           'user': canvas_fields['user_display_name']})

        return HttpResponseRedirect(
            reverse('instructor:instructor_home',
                    kwargs={'course_id': course_id}) + '?login_redirect=True')

    elif 'TaEnrollment' in canvas_fields['role']:
        utils.set_user_course(canvas_fields, models.Roles.TA)
        auth.authenticate_login(request, canvas_fields)

        course = models.Course.objects.get(pk=course_id)
        logger.info('TA login',
                    extra={'course': str(course),
                           'user': canvas_fields['user_display_name']})

        return HttpResponseRedirect(
            reverse('instructor:instructor_home',
                    kwargs={'course_id': course_id}) + '?login_redirect=True')

    elif 'StudentEnrollment' in canvas_fields['role']:
        utils.set_user_course(canvas_fields, models.Roles.STUDENT)
        auth.authenticate_login(request, canvas_fields)

        course = models.Course.objects.get(pk=course_id)
        logger.info('Student login',
                    extra={'course': str(course),
                           'user': canvas_fields['user_display_name']})

        return HttpResponseRedirect(
            reverse('student:student_home',
                    kwargs={'course_id': course_id}))

    else:
        logger.info(f"ROLE NOT DEFINED: {canvas_fields['role']}",
                    extra={'course': course_id,
                           'user': canvas_fields['user_display_name']})
        return HttpResponseServerError(f"Your role in course {course_id} is not defined. Please contact it@landfood.ubc.ca for assistance.")

def get_jwks(request):
    tool_conf = utils.get_tool_conf()
    return JsonResponse(tool_conf.get_jwks(), safe=False)
