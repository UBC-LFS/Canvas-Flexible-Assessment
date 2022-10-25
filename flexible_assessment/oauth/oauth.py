import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.contrib import messages
from django.http.response import HttpResponseRedirect
from django.urls import reverse
from django.utils.crypto import get_random_string

from oauth import canvas_oauth
from oauth.exceptions import InvalidOAuthStateError, MissingTokenError
from oauth.models import CanvasOAuth2Token


class FernetCanvas(Fernet):
    def __init__(self):
        key = base64.urlsafe_b64encode(PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=settings.ENCRYPT_SALT.encode('utf-8'),
            iterations=100000,
            backend=default_backend()
        ).derive(settings.ENCRYPT_PASSWORD.encode('utf-8')))

        super().__init__(key)


def get_oauth_token(request):
    try:
        oauth_token = request.user.oauth2_token
    except CanvasOAuth2Token.DoesNotExist:
        raise MissingTokenError("No token found for user %s" % request.user.pk)

    if oauth_token.expires_within(
            settings.CANVAS_OAUTH_TOKEN_EXPIRATION_BUFFER):
        oauth_token = refresh_oauth_token(request)

    fernet = FernetCanvas()

    return fernet.decrypt(bytes(oauth_token.access_token)).decode('utf-8')


def handle_missing_or_invalid_token(request):
    request.session["canvas_oauth_initial_uri"] = request.get_full_path()

    oauth_request_state = get_random_string(32)
    request.session["canvas_oauth_request_state"] = oauth_request_state

    oauth_redirect_uri = request.build_absolute_uri(
        reverse('canvas-oauth-callback'))
    request.session["canvas_oauth_redirect_uri"] = oauth_redirect_uri

    authorize_url = canvas_oauth.get_oauth_login_url(
        settings.CANVAS_OAUTH_CLIENT_ID,
        redirect_uri=oauth_redirect_uri,
        state=oauth_request_state,
        scopes=settings.CANVAS_OAUTH_SCOPES)

    return HttpResponseRedirect(authorize_url)


def oauth_callback(request):
    error = request.GET.get('error_description')
    if error:
        return error_redirect(request, error)
    code = request.GET.get('code')
    state = request.GET.get('state')

    if state != request.session['canvas_oauth_request_state']:
        raise InvalidOAuthStateError("OAuth state mismatch!")

    access_token, expires, refresh_token = canvas_oauth.get_access_token(
        grant_type='authorization_code',
        client_id=settings.CANVAS_OAUTH_CLIENT_ID,
        client_secret=settings.CANVAS_OAUTH_CLIENT_SECRET,
        redirect_uri=request.session["canvas_oauth_redirect_uri"],
        code=code)

    fernet = FernetCanvas()

    binary_access_token = fernet.encrypt(access_token.encode('utf-8'))
    binary_refresh_token = fernet.encrypt(refresh_token.encode('utf-8'))

    CanvasOAuth2Token.objects.get_or_create(
        user=request.user,
        access_token=binary_access_token,
        expires=expires,
        refresh_token=binary_refresh_token)

    initial_uri = request.session['canvas_oauth_initial_uri']

    return HttpResponseRedirect(initial_uri)


def refresh_oauth_token(request):
    oauth_token = request.user.oauth2_token

    fernet = FernetCanvas()

    binary_refresh_token = oauth_token.refresh_token
    refresh_token = fernet.decrypt(bytes(binary_refresh_token)).decode('utf-8')

    access_token, expires, _ = canvas_oauth.get_access_token(
        grant_type='refresh_token',
        client_id=settings.CANVAS_OAUTH_CLIENT_ID,
        client_secret=settings.CANVAS_OAUTH_CLIENT_SECRET,
        redirect_uri=request.build_absolute_uri(
            reverse('canvas-oauth-callback')),
        refresh_token=refresh_token)

    oauth_token.access_token = fernet.encrypt(access_token.encode('utf-8'))
    oauth_token.expires = expires

    oauth_token.save()

    return oauth_token


def error_redirect(request, error_message):
    messages.error(request, error_message)
    course_id = request.session.pop('course_id', '')
    return HttpResponseRedirect(reverse('instructor:instructor_home',
                                        kwargs={'course_id': course_id}))
