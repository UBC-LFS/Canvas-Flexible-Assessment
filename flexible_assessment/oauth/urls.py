from django.urls import path
from .oauth import oauth_callback

urlpatterns = [
    path('oauth-callback', oauth_callback, name='canvas-oauth-callback'),
]
