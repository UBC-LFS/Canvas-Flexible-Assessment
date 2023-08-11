from django.test import TestCase, tag
from django.forms import ValidationError
import flexible_assessment.models as models 
from flexible_assessment.tests.test_data import DATA
import flexible_assessment.utils as utils
from flexible_assessment.tests.mock_classes import *
import instructor.forms as forms

import flexible_assessment.tests.mock_classes as mock_classes
import types

class TestUtils(TestCase):
    fixtures = DATA

    @mock_classes.use_mock_canvas(location="flexible_assessment.utils.FlexCanvas")
    def test_add_new_students(self, mocked_flex_canvas_instance):
        """ Currently in Course 4 there is only one student (test_student1). Make sure new users on Canvas are added to the database """
        course_id = 4
        course = models.Course.objects.filter(id=course_id).first()
        users = models.UserCourse.objects.filter(course=course_id)
        
        self.assertEqual(users.count(), 2) # Instructor 1 and student 1
        
        student_profiles = models.UserProfile.objects.filter(display_name__contains='student')
        def mock_get_users(self, **kwargs):
            return [mock_classes.MockUser(student.display_name, student.pk) for student in list(student_profiles)]
        
        mock_course = mocked_flex_canvas_instance.get_course(1)
        mock_course.get_users = types.MethodType(mock_get_users, mock_course) # Add the get_users method to this instance of MockCanvasCourse
        
        utils.update_students("request", course)
        
        users_after = models.UserCourse.objects.filter(course=course_id)
        self.assertEqual(users_after.count(), student_profiles.count() + 1) # all students + 1 instructor are now in course
    
    @mock_classes.use_mock_canvas(location="flexible_assessment.utils.FlexCanvas")
    def test_remove_students(self, mocked_flex_canvas_instance):
        """ Currently in Course 1 there are multiple students. If all these students are removed from the Canvas course, make sure they are deleted from the database """
        course_id = 1
        course = models.Course.objects.filter(id=course_id).first()
        
        student_profiles = models.UserProfile.objects.filter(display_name__contains='student')
        def mock_get_users(self, **kwargs):
            return []
        
        mock_course = mocked_flex_canvas_instance.get_course(1)
        mock_course.get_users = types.MethodType(mock_get_users, mock_course) # Add the get_users method to this instance of MockCanvasCourse
        
        utils.update_students("request", course)
        
        non_students = models.UserCourse.objects.filter(course=course_id).exclude(role=models.Roles.STUDENT)
        users_after = models.UserCourse.objects.filter(course=course_id)
        self.assertEqual(users_after.count(), non_students.count()) # There are no more students in the course
        
    def test_set_user_profile(self):
        """ Make sure new users are created, and existing user is returned """
        non_existant_key = 100000
        user_set = models.UserProfile.objects.filter(pk=non_existant_key)
        self.assertFalse(user_set.exists())
        
        user = utils.set_user_profile(non_existant_key, "New Login Id", "New Display Name")
        self.assertTrue(user_set.exists())
        self.assertEqual(user.user_id, non_existant_key)
        self.assertEqual(user.login_id, "New Login Id")
        self.assertEqual(user.display_name, "New Display Name")
        
        existing_user = models.UserProfile.objects.filter(pk=1)
        self.assertTrue(existing_user.exists())
        
        user = utils.set_user_profile(1, "Some ID", "Some Name")
        self.assertEqual(user.user_id, 1)
        self.assertEqual(user.login_id, "test_student1")
        self.assertEqual(user.display_name, "test_student1")
    
    def test_set_course(self):
        """ Make sure new courses are created, and existing course is returned """
        non_existant_id = 100000
        course_set = models.Course.objects.filter(pk=non_existant_id)
        self.assertFalse(course_set.exists())
        
        course = utils.set_course(non_existant_id, "New Course Title")
        self.assertTrue(course_set.exists())
        self.assertEqual(course.id, non_existant_id)
        self.assertEqual(course.title, "New Course Title")
        
        existing_course = models.Course.objects.filter(pk=1)
        self.assertTrue(existing_course.exists())
        
        course = utils.set_course(1, "Some Course")
        self.assertEqual(course.id, 1)
        self.assertEqual(course.title, "test_course1")
    
    def test_set_user_course_enrollment(self):
        """ Make sure new UserCourses are created"""
        course_id = 1000
        student_id = 1
        existing_student = models.UserProfile.objects.filter(pk=student_id).first()
        existing_course = models.Course.objects.filter(pk=course_id).first()
        
        user_course_set = models.UserCourse.objects.filter(user_id=existing_student.user_id, course_id=course_id)
        self.assertFalse(user_course_set.exists())
        
        utils.set_user_course_enrollment(existing_student, existing_course, models.Roles.STUDENT)
        self.assertTrue(user_course_set.exists())
        new_user_course = user_course_set.first()
        self.assertEqual(new_user_course.user_id, student_id)
        self.assertEqual(new_user_course.course, existing_course)
        self.assertEqual(new_user_course.role, models.Roles.STUDENT)
    
    def test_set_user_comment(self):
        """ Make sure new User Comments are created"""
        course_id = 1000
        student_id = 1
        existing_student = models.UserProfile.objects.filter(pk=student_id).first()
        existing_course = models.Course.objects.filter(pk=course_id).first()
        
        user_comment_set = existing_student.usercomment_set.filter(course__id=course_id)
        self.assertFalse(user_comment_set.exists())
        
        utils.set_user_comment(existing_student, existing_course)
        self.assertTrue(user_comment_set.exists())
        new_user_comment = user_comment_set.first()
        self.assertEqual(new_user_comment.user, existing_student)
        self.assertEqual(new_user_comment.course, existing_course)
        self.assertEqual(new_user_comment.comment, "")
    
    def test_set_user_course(self):
        """ Make sure all relevant database items are created """
        course_id = 99999
        student_id = 99999
        
        canvas_fields = {}
        canvas_fields['user_id'] = student_id
        canvas_fields['login_id'] = "New login id"
        canvas_fields['user_display_name'] = "New display name"
        canvas_fields['course_id'] = course_id
        canvas_fields['course_name'] = "New course name"
        
        user_set = models.UserProfile.objects.filter(pk=student_id)
        self.assertFalse(user_set.exists())
        course_set = models.Course.objects.filter(pk=course_id)
        self.assertFalse(course_set.exists())
        user_course_set = models.UserCourse.objects.filter(user_id=student_id, course_id=course_id)
        self.assertFalse(user_course_set.exists())
        
        utils.set_user_course(canvas_fields, models.Roles.STUDENT)
        
        self.assertTrue(user_set.exists())
        self.assertTrue(course_set.exists())
        self.assertTrue(user_course_set.exists())
        created_student = models.UserProfile.objects.filter(pk=student_id).first()
        user_comment_set = created_student.usercomment_set.filter(course__id=course_id)
        self.assertTrue(user_comment_set.exists())
    

    def test_assessments_min_impossible(self):
        """ If they use this min, they won't be able to reach 100 """
        data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '',
            'form-0-title': 'Assignment1',
            'form-0-default': '50',
            'form-0-min': '50',
            'form-0-max': '51',
            'form-1-title': 'Assignment2',
            'form-1-default': '50',
            'form-1-min': '48',
            'form-1-max': '50',
        }
        AssessmentFormSet = forms.get_assessment_formset()
        formset = AssessmentFormSet(data)
        self.assertFalse(formset.is_valid())

        form_errors = ' '.join(str(form.errors) for form in formset.forms)

        target_error = "Please increase to 49"
        self.assertIn(target_error, form_errors)

    def test_assessments_max_impossible(self):
        """ If they use this max, they always go above 100 """
        data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '',
            'form-0-title': 'Assignment1',
            'form-0-default': '50',
            'form-0-min': '50',
            'form-0-max': '52',
            'form-1-title': 'Assignment2',
            'form-1-default': '50',
            'form-1-min': '49',
            'form-1-max': '50',
        }
        AssessmentFormSet = forms.get_assessment_formset()
        formset = AssessmentFormSet(data)
        self.assertFalse(formset.is_valid())
        form_errors = ' '.join(str(form.errors) for form in formset.forms)

        target_error = "Please decrease to 51"
        self.assertIn(target_error, form_errors)