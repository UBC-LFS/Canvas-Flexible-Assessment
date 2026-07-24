from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse
from canvasapi.exceptions import Unauthorized
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from oauth.middleware import OAuthMiddleware
from oauth.oauth import error_redirect, oauth_callback


class TestOAuthMiddleware(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = OAuthMiddleware(lambda request: None)

    def test_process_exception_stores_accommodations_course_id(self):
        request = self.factory.get("/accommodations/150/")
        request.session = {}

        self.middleware.process_exception(request, Exception("ignored"))

        self.assertEqual(request.session["course_id"], "150")

    def test_process_exception_stores_student_course_id(self):
        request = self.factory.get("/flexible_assessment/student/150/")
        request.session = {}

        self.middleware.process_exception(request, Exception("ignored"))

        self.assertEqual(request.session["course_id"], "150")

    @patch("oauth.middleware.handle_missing_or_invalid_token")
    def test_process_exception_redirects_unauthorized_to_oauth(
        self, mock_handle_missing_or_invalid_token
    ):
        request = self.factory.get("/accommodations/150/")
        request.session = {}
        mock_handle_missing_or_invalid_token.return_value = "oauth redirect"

        response = self.middleware.process_exception(
            request, Unauthorized([{"message": "Insufficient scopes on access token."}])
        )

        self.assertEqual(response, "oauth redirect")
        self.assertEqual(request.session["course_id"], "150")


class TestOAuthErrorRedirect(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("oauth.oauth.messages.error")
    def test_error_redirect_prefers_initial_uri(self, mock_messages_error):
        request = self.factory.get("/oauth/oauth-callback/")
        request.session = {
            "canvas_oauth_initial_uri": "/accommodations/150/?login_redirect=True",
            "course_id": "150",
        }

        response = error_redirect(request, "invalid scope")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/accommodations/150/?login_redirect=True")

    @patch("oauth.oauth.messages.error")
    def test_error_redirect_uses_login_when_course_id_missing(self, mock_messages_error):
        request = self.factory.get("/oauth/oauth-callback/")
        request.session = {}

        response = error_redirect(request, "invalid scope")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))


class TestOAuthCallback(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("oauth.oauth.CanvasOAuth2Token.objects.update_or_create")
    @patch("oauth.oauth.FernetCanvas")
    @patch("oauth.oauth.canvas_oauth.get_access_token")
    def test_oauth_callback_replaces_existing_token(
        self, mock_get_access_token, mock_fernet_canvas, mock_update_or_create
    ):
        request = self.factory.get(
            "/oauth/oauth-callback/", {"code": "auth-code", "state": "valid-state"}
        )
        request.session = {
            "canvas_oauth_request_state": "valid-state",
            "canvas_oauth_redirect_uri": "https://example.test/oauth/oauth-callback/",
            "canvas_oauth_initial_uri": "/accommodations/150/?login_redirect=True",
        }
        request.user = SimpleNamespace(pk=123)

        mock_get_access_token.return_value = (
            "new-access-token",
            "expiry-time",
            "new-refresh-token",
        )
        fernet = MagicMock()
        fernet.encrypt.side_effect = [b"encrypted-access", b"encrypted-refresh"]
        mock_fernet_canvas.return_value = fernet

        response = oauth_callback(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/accommodations/150/?login_redirect=True")
        mock_update_or_create.assert_called_once_with(
            user=request.user,
            defaults={
                "access_token": b"encrypted-access",
                "expires": "expiry-time",
                "refresh_token": b"encrypted-refresh",
            },
        )
