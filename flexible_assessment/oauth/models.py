from django.db import models
from django.conf import settings
from django.utils import timezone


class CanvasOAuth2Token(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='oauth2_token',
    )

    access_token = models.TextField()
    refresh_token = models.TextField()
    expires = models.DateTimeField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def expires_within(self, delta):
        if not self.expires:
            return False

        return self.expires - timezone.now() <= delta

    def __str__(self):
        return "OAuth2 {}".format(self.user)
