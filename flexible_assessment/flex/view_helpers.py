import json
import os

from django.conf import settings
from pylti1p3.contrib.django import DjangoCacheDataStorage
from pylti1p3.tool_config import ToolConfJsonFile

from .models import UserProfile


def set_user_profile(request, custom_fields, role):
    user_id_set = UserProfile.objects.all().filter(user_id__exact=custom_fields['user_id'])
    if not user_id_set.exists():
        user_id = custom_fields['user_id']
        login_id = custom_fields['login_id']
        display_name = custom_fields['user_display_name']
        user = UserProfile.objects.create_user(user_id, login_id, display_name, role)
    else:
        user = user_id_set.first()
    request.session['user_id'] = user.user_id
    request.session['display_name'] = user.display_name
    return user

def get_launch_data_storage():
    return DjangoCacheDataStorage()


def get_launch_url(request):
    target_link_uri = request.POST.get('target_link_uri', request.GET.get('target_link_uri'))
    if not target_link_uri:
        raise Exception('Missing "target_link_uri" param')

    return target_link_uri

def get_lti_config_path():
    return os.path.join(settings.BASE_DIR, 'configs', 'flexible_assessment.json')

def get_tool_conf():
    tool_conf = ToolConfJsonFile(get_lti_config_path())
    return tool_conf
    