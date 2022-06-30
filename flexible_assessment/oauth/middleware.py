import re

from canvasapi.exceptions import InvalidAccessToken

from oauth.exceptions import CanvasOAuthError, MissingTokenError
from oauth.oauth import error_redirect, handle_missing_or_invalid_token


class OAuthMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        course_id_match = re.findall(r'\/instructor\/(\d*)\/', request.path)
        if course_id_match:
            course_id = course_id_match[0]
            request.session['course_id'] = course_id

        if isinstance(exception, MissingTokenError):
            return handle_missing_or_invalid_token(request)
        elif isinstance(exception, CanvasOAuthError):
            return error_redirect(request, str(exception))
        elif isinstance(exception, InvalidAccessToken):
            return handle_missing_or_invalid_token(request)
        return
