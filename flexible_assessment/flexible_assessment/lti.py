import os

from django.conf import settings
from pylti1p3.contrib.django import DjangoCacheDataStorage
from pylti1p3.tool_config import ToolConfJsonFile


def get_launch_data_storage():
    return DjangoCacheDataStorage()


def get_launch_url(request):
    target_link_uri = request.POST.get(
        "target_link_uri", request.GET.get("target_link_uri")
    )
    if not target_link_uri:
        raise Exception('Missing "target_link_uri" param')

    return target_link_uri


def get_lti_config_path():
    return os.path.join(settings.BASE_DIR, "configs", settings.LTI_CONFIG)


def get_tool_conf():
    tool_conf = ToolConfJsonFile(get_lti_config_path())
    return tool_conf
