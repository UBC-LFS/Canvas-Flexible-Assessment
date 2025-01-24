from django.test import TestCase, RequestFactory
from unittest.mock import patch
from instructor.canvas_api import FlexCanvas
from django.conf import settings


class TestFlexCanvas(TestCase):
    # need to test that get_flat_groups_and_enrollments() ignores unpublished assignments
    pass
