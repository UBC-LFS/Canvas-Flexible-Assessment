from oauth.exceptions import (MissingTokenError, CanvasOAuthError)
from oauth.oauth import (handle_missing_token, error_redirect)
from canvasapi.exceptions import InvalidAccessToken


class OAuthMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        print(exception)
        if isinstance(exception, MissingTokenError):
            return handle_missing_token(request)
        elif isinstance(exception, CanvasOAuthError):
            return error_redirect(request, str(exception))
        elif isinstance(exception, InvalidAccessToken):
            error_messages = [error['message'] for error in exception.message if 'message' in error]
            return error_redirect(request, ' '.join(error_messages))
        return
