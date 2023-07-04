import flexible_assessment.models as models
from django.test import TestCase, RequestFactory, Client, tag
from django.urls import reverse
from django.http import HttpResponseRedirect
from unittest.mock import patch, MagicMock, ANY
from flexible_assessment.views import login
from pylti1p3.exception import LtiException

class TestLogin(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.login_url = reverse('login')
        self.client = Client()
    
    def test_login(self):
        url = reverse('login')
        request = self.factory.get(url)
        
        with patch('flexible_assessment.lti.get_tool_conf'), \
             patch('flexible_assessment.lti.get_launch_data_storage'), \
             patch('flexible_assessment.lti.get_launch_url') as mock_get_launch_url, \
             patch('flexible_assessment.views.DjangoOIDCLogin') as mock_DjangoOIDCLogin:
            mock_get_launch_url.return_value = 'https://example.com'
            mock_oidc_login = MagicMock()
            mock_oidc_login.enable_check_cookies.return_value = mock_oidc_login
            mock_oidc_login.redirect.return_value = 'mock response'
            mock_DjangoOIDCLogin.return_value = mock_oidc_login
            
            response = login(request)
            
            mock_get_launch_url.assert_called_once_with(request)
            mock_DjangoOIDCLogin.assert_called_once_with(request, ANY, launch_data_storage=ANY)
            mock_oidc_login.enable_check_cookies.assert_called_once()
            mock_oidc_login.redirect.assert_called_once_with('https://example.com')
            self.assertEqual(response, 'mock response')
            

    def test_login_success(self):
        # Mock the lti module functions used in the login view
        with patch('flexible_assessment.lti.get_tool_conf') as mock_get_tool_conf, \
                patch('flexible_assessment.lti.get_launch_data_storage') as mock_get_launch_data_storage, \
                patch('flexible_assessment.lti.get_launch_url', return_value=reverse('launch')):

            request = self.factory.get(self.login_url)

            # Mock the DjangoOIDCLogin object and its methods
            with patch('flexible_assessment.views.DjangoOIDCLogin') as mock_django_oidc_login:
                oidc_login_instance = MagicMock()
                oidc_login_instance.enable_check_cookies.return_value = oidc_login_instance
                oidc_login_instance.redirect.return_value = HttpResponseRedirect(reverse('launch'))
                mock_django_oidc_login.return_value = oidc_login_instance

                response = login(request)

                self.assertEqual(response.status_code, 302)  # 302 indicates HttpResponseRedirect
                self.assertTrue(response.url.startswith(reverse('launch')))
                
    
    def test_login_lti_exception(self):
        print('-----------------------TESTING LOGIN LTI EXCEPTION----------------------------------------------')
        # Mock the lti module functions used in the login view
        with patch('flexible_assessment.lti.get_tool_conf') as mock_get_tool_conf, \
                patch('flexible_assessment.lti.get_launch_data_storage') as mock_get_launch_data_storage, \
                patch('flexible_assessment.lti.get_launch_url', return_value=reverse('launch')):

            request = self.factory.get(self.login_url)

            # Mock the DjangoOIDCLogin object and its methods
            with patch('flexible_assessment.views.DjangoOIDCLogin') as mock_django_oidc_login:
                oidc_login_instance = MagicMock()
                oidc_login_instance.enable_check_cookies.side_effect = LtiException("Unable to find deployment")
                mock_django_oidc_login.return_value = oidc_login_instance

                response = login(request)

                # Check if the response is an error (400 Bad Request)
                self.assertEqual(response.status_code, 400)
                self.assertIn("deployment ID key issue", response.content.decode())

    def test_login_generic_exception(self):
        # Mock the lti module functions used in the login view
        with patch('flexible_assessment.lti.get_tool_conf') as mock_get_tool_conf, \
                patch('flexible_assessment.lti.get_launch_data_storage') as mock_get_launch_data_storage, \
                patch('flexible_assessment.lti.get_launch_url', return_value=reverse('launch')):

            request = self.factory.get(self.login_url)

            # Mock the DjangoOIDCLogin object and its methods
            with patch('flexible_assessment.views.DjangoOIDCLogin') as mock_django_oidc_login:
                oidc_login_instance = MagicMock()
                oidc_login_instance.enable_check_cookies.side_effect = Exception("Some generic error")
                mock_django_oidc_login.return_value = oidc_login_instance

                response = login(request)

                # Check if the response is an error (500 Internal Server Error)
                self.assertEqual(response.status_code, 500)
                self.assertIn("An error occurred during login.", response.content.decode())
