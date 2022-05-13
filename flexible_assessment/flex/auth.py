from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth.backends import BaseBackend
from django.http import HttpResponse

from .models import UserProfile


class SettingsBackend(BaseBackend):
    """Extends authentication backend for authenticating custom user

    Methods
    -------
    authenticate(request)
        Authenticates user and retrieves the user if they exist
    get_user(user_id)
        Gets user using user id as primary key
    """

    def authenticate(self, request):
        """Authenticates custom user based on session information
        and retrieves the user if they exist

        Parameters
        ----------
        request : request
            Containes request data

        Returns
        -------
        Union[None, User]
            User instance if one with user_id exists or None otherise
        """

        user_id = request.session['user_id']
        login_id = request.session['login_id']
        role = request.session['role']

        if user_id and login_id and role:
            try:
                user = UserProfile.objects.get(pk=user_id)
                if user.login_id == login_id and user.role == role:
                    return user
            except UserProfile.DoesNotExist:
                return None

        return None

    def get_user(self, user_id):
        try:
            return UserProfile.objects.get(pk=user_id)
        except UserProfile.DoesNotExist:
            return None


def authenticate_login(request):
    """Authenticates and logs in current user using session data

    Parameters
    ----------
    request : request
        Contains request data
    """

    user = authenticate(request)
    if user is not None:
        auth_login(request, user)
