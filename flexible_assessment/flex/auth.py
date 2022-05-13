from django.contrib.auth.backends import BaseBackend
from .models import UserProfile


class SettingsBackend(BaseBackend):
    def authenticate(self, request):
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
