from django.urls import reverse
from django.http.response import HttpResponseRedirect
from django.utils.crypto import get_random_string
from django.conf import settings
from django.contrib import messages

from oauth import canvas_oauth
from oauth.models import CanvasOAuth2Token
from oauth.exceptions import (
    MissingTokenError, InvalidOAuthStateError)


def get_oauth_token(request):
    try:
        oauth_token = request.user.oauth2_token
    except CanvasOAuth2Token.DoesNotExist:
        raise MissingTokenError("No token found for user %s" % request.user.pk)

    if oauth_token.expires_within(
            settings.CANVAS_OAUTH_TOKEN_EXPIRATION_BUFFER):
        oauth_token = refresh_oauth_token(request)

    return oauth_token.access_token


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
    error = request.GET.get('error')
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

    if not CanvasOAuth2Token.objects.filter(user=request.user):
        CanvasOAuth2Token.objects.create(
            user=request.user,
            access_token=access_token,
            expires=expires,
            refresh_token=refresh_token)
    else:
        oauth_user = CanvasOAuth2Token.objects.get(user=request.user)
        oauth_user.access_token = access_token
        oauth_user.expires = expires
        oauth_user.refresh_token = refresh_token
        oauth_user.save()

    initial_uri = request.session['canvas_oauth_initial_uri']

    return HttpResponseRedirect(initial_uri)


def refresh_oauth_token(request):
    oauth_token = request.user.oauth2_token

    oauth_token.access_token, oauth_token.expires, _ = canvas_oauth \
        .get_access_token(
            grant_type='refresh_token',
            client_id=settings.CANVAS_OAUTH_CLIENT_ID,
            client_secret=settings.CANVAS_OAUTH_CLIENT_SECRET,
            redirect_uri=request.build_absolute_uri(
                reverse('canvas-oauth-callback')),
            refresh_token=oauth_token.refresh_token)

    oauth_token.save()

    return oauth_token


def error_redirect(request, error_message):
    messages.error(request, error_message)
    course_id = request.session.pop('course_id', '')
    return HttpResponseRedirect(reverse('instructor:instructor_home',
                                        kwargs={'course_id': course_id}))
