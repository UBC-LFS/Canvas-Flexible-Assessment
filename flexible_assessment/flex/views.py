import os
import pprint

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from pylti1p3.contrib.django import (DjangoCacheDataStorage, DjangoMessageLaunch, DjangoOIDCLogin)
from pylti1p3.tool_config import ToolConfJsonFile


def index(request):
    return HttpResponse("Home page")


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


def login(request):
    tool_conf = get_tool_conf()
    launch_data_storage = get_launch_data_storage()
    pprint.pprint(request)

    oidc_login = DjangoOIDCLogin(request, tool_conf, launch_data_storage=launch_data_storage)
    target_link_uri = get_launch_url(request)
    return oidc_login\
        .enable_check_cookies()\
        .redirect(target_link_uri)


@require_POST
def launch(request):
    tool_conf = get_tool_conf()
    launch_data_storage = get_launch_data_storage()
    message_launch = DjangoMessageLaunch(request, tool_conf, launch_data_storage=launch_data_storage)
    message_launch_data = message_launch.get_launch_data()
    pprint.pprint(message_launch_data['https://purl.imsglobal.org/spec/lti/claim/custom'])

    return HttpResponse("Launch successful")

def get_jwks(request):
    tool_conf = get_tool_conf()
    return JsonResponse(tool_conf.get_jwks(), safe=False)
