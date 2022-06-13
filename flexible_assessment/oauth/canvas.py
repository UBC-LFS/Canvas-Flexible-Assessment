from datetime import timedelta

import requests
from django.utils import timezone

from oauth.exceptions import InvalidOAuthReturnError
from django.conf import settings


def get_oauth_login_url(client_id, redirect_uri, response_type='code',
                        state=None, scopes=None, purpose=None,
                        force_login=None):
    authorize_url = settings.CANVAS_OAUTH_AUTHORIZE_URL
    scopes = " ".join(scopes) if scopes else None  

    auth_request_params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': response_type,
        'state': state,
        'scope': scopes,
        'purpose': purpose,
        'force_login': force_login,
    }

    auth_request = requests.Request('GET', authorize_url,
                                    params=auth_request_params)
                
    return auth_request.prepare().url


def get_access_token(grant_type, client_id, client_secret, redirect_uri,
                     code=None, refresh_token=None):
    oauth_token_url = settings.CANVAS_OAUTH_ACCESS_TOKEN_URL
    post_params = {
        'grant_type': grant_type,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
    }

    if grant_type == 'authorization_code':
        post_params['code'] = code
    else:
        post_params['refresh_token'] = refresh_token

    r = requests.post(oauth_token_url, post_params)
    if r.status_code != 200:
        raise InvalidOAuthReturnError("%s request failed to get a token: %s" % (
            grant_type, r.text))

    response_data = r.json()
    access_token = response_data['access_token']
    seconds_to_expire = response_data['expires_in']
    expires = timezone.now() + timedelta(seconds=seconds_to_expire)

    refresh_token = None
    if 'refresh_token' in response_data:
        refresh_token = response_data['refresh_token']

    return (access_token, expires, refresh_token)
