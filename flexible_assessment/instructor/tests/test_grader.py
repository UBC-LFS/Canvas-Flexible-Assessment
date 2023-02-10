from django.test import TestCase
from flexible_assessment.models import UserProfile
from instructor import grader
from flexible_assessment.models import Roles, FlexAssessment, Assessment, Course
from flexible_assessment.tests.mock_classes import *

from unittest.mock import patch
from flexible_assessment.tests.test_data import DATA

class TestGrader(TestCase):
    fixtures = DATA
    
    def build_group_dict(self, student_ids, all_grades, weights):
        """
        Helper function to quickly return the groups dictionary grader.py uses
    
        Assumes:
        Assignment Group indexes start from 1
        all_grades is at least as long as how many assignment groups there are
        each grade_list in all_grades is at least as long as how many students there are
        weights list is at least as long as how many assignments there are and weights add to 100
        
        Parameters:
        students: 1d list of students in this course
        all_grades: 2d array of grade data. Example: [[50, 25, 20, 50], [100, 30, 40, 60]]. Are the grades for students 1- 4 for groups 1 - 2
        weights: 1d array of weights to be applied for each assignment group
    
        Returns:
        dict - Example: {'1': {'group_weight': 25, 'grade_list': {'grades': [('1', 50), ('2', 25), ('3', 30), ('4', 50)]}}, 
                '2': {'group_weight': 25, 'grade_list': {'grades': [('1', 50), ('2', 25), ('3', 30), ('4', 50)]}}, 
                '3': {'group_weight': 25, 'grade_list': {'grades': [('1', 50), ('2', 25), ('3', 30), ('4', 50)]}}, 
                '4': {'group_weight': 25, 'grade_list': {'grades': [('1', 50), ('2', 25), ('3', 30), ('4', 50)]}}}
                for students with id of '1', '2', '3', '4' in students
        """
        # Transform [[50, 25, 20, 50], [100, 30, 40, 60], ...] into [[('1', 50), ('2', 25), ('3', 20), ('4', 50)], [('1', 100), ('2', 30), ('3', 40), ('4', 60)]]
        grade_tuples = []
        for grade_list in all_grades:
            grades_x = []
            for index in range(len(grade_list)):
                grades_x.append((student_ids[index], grade_list[index]))
            grade_tuples.append(grades_x)
            
        group_dict = {}
        for index, grade_list in enumerate(grade_tuples):
            group = MockAssignmentGroup(f"test_group{index}", index)
            group.grade_list = {"grades": grade_list}
            group.group_weight = weights[index]
            group_dict[str(index + 1)] = group.asdict()
            
        return group_dict
    
    def bulk_create_flexes_for_student(self, student, assessments, flexes):
        """
        Helper function to quickly set a student's flexes
        
        Assumes:
        len(flexes) == len(assessments)
        
        Paramters:
        student: UserProfile
        assessments: Assessment
        flexes: int[]
        
        """
        flex_assessments = [
            FlexAssessment(
                user=student,
                flex=flexes[index],
                assessment=assessment) for index, assessment in enumerate(assessments)]
        FlexAssessment.objects.bulk_create(flex_assessments)
    
    def test_Grader_calculates_default_grade_correct_same_weights(self):
        course_id = 1
        students = UserProfile.objects.filter(usercourse__role=Roles.STUDENT, usercourse__course__id=course_id)
        student_ids = [str(student.user_id) for student in students]
        
        # Course_id 1 has 4 assignment groups
        groups_dict = self.build_group_dict(student_ids, [[70, 25.5, 100/3, 200/3], [80, 36.7, 50.4534, 200/3], [90, 75, 100, 200/3], [100, 0, 1.112, 200/3]],
                                            weights=[25, 25, 25, 25])
        
        self.assertEqual(grader.get_default_total(groups_dict, students[0]), 85.00)
        self.assertEqual(grader.get_default_total(groups_dict, students[1]), 34.30)
        self.assertEqual(grader.get_default_total(groups_dict, students[2]), 46.22)
        self.assertEqual(grader.get_default_total(groups_dict, students[3]), 66.67)
        
    def test_Grader_calculates_default_grade_correct_different_weights(self):
        course_id = 1
        students = UserProfile.objects.filter(usercourse__role=Roles.STUDENT, usercourse__course__id=course_id)
        student_ids = [str(student.user_id) for student in students]
        
        # Course_id 1 has 4 assignment groups
        groups_dict = self.build_group_dict(student_ids, [[70, 25.5, 100/3, 200/3], [80, 36.7, 50.4534, 200/3], [90, 75, 100, 200/3], [100, 0, 1.112, 200/3]],
                                            weights=[50, 0, 10, 40])
        
        self.assertEqual(grader.get_default_total(groups_dict, students[0]), 84.00)
        self.assertEqual(grader.get_default_total(groups_dict, students[1]), 20.25)
        self.assertEqual(grader.get_default_total(groups_dict, students[2]), 27.11)
        self.assertEqual(grader.get_default_total(groups_dict, students[3]), 66.67)
    
    def test_Grader_determines_if_flex_is_valid_correctly(self):
        """ A student's flex is valid if all add up to 100 and none of them are None"""
        course_id = 1
        course = Course.objects.filter(id=course_id).first()
        students = UserProfile.objects.filter(usercourse__role=Roles.STUDENT, usercourse__course__id=course_id)
        # There are 4 assessments in course of id 1
        assessments = Assessment.objects.filter(course_id=course_id)
        for student in students:
            flexes = student.flexassessment_set.filter(assessment__course=course_id)
            flexes.delete() # Delete the predefined flexes in the fixtures
            
        self.bulk_create_flexes_for_student(students[0], assessments, [10, 20, 30, 40])
        self.bulk_create_flexes_for_student(students[1], assessments, [10, 20, 70, None])
        self.bulk_create_flexes_for_student(students[2], assessments, [50, 10, 20, 1])
        
        self.assertTrue(grader.valid_flex(students[0], course))
        self.assertFalse(grader.valid_flex(students[1], course))
        self.assertFalse(grader.valid_flex(students[2], course))
    
    def test_Grader_calculates_override_total_correctly(self):
        course_id = 1
        course = Course.objects.filter(id=course_id).first()
        students = UserProfile.objects.filter(usercourse__role=Roles.STUDENT, usercourse__course__id=course_id)
        student_ids = [str(student.user_id) for student in students]
        
        # Course_id 1 has 4 assignment groups
        groups_dict = self.build_group_dict(student_ids, [[70, 25.5, 100/3, 200/3], [80, 36.7, 50.4534, 200/3], [90, 75, 100, 200/3], [100, 0, 1.112, 200/3]],
                                            weights=[50, 0, 10, 40])
    
        # There are 4 assessments in course of id 1
        assessments = Assessment.objects.filter(course_id=course_id)
        for student in students:
            flexes = student.flexassessment_set.filter(assessment__course=course_id)
            flexes.delete() # Delete the predefined flexes in the fixtures
            
        self.bulk_create_flexes_for_student(students[0], assessments, [50, 0, 10, 40]) # This matches the default weights
        self.bulk_create_flexes_for_student(students[1], assessments, [100, None, None, None])
        self.bulk_create_flexes_for_student(students[2], assessments, [60, 20, 10, 10]) # Different from default weights
        self.bulk_create_flexes_for_student(students[3], assessments, [50, 10, 20, 1]) # This doesn't sum to 100
        
        self.assertEqual(grader.get_override_total(groups_dict, students[0], course), 84.00)
        self.assertEqual(grader.get_override_total(groups_dict, students[1], course), None)
        self.assertEqual(grader.get_override_total(groups_dict, students[2], course), 40.20)
        self.assertEqual(grader.get_override_total(groups_dict, students[3], course), None)
    
    def test_Grader_gets_averages_correctly(self):
        course_id = 1
        course = Course.objects.filter(id=course_id).first()
        students = UserProfile.objects.filter(usercourse__role=Roles.STUDENT, usercourse__course__id=course_id)
        student_ids = [str(student.user_id) for student in students]
        
        # Course_id 1 has 4 assignment groups
        groups_dict = self.build_group_dict(student_ids, [[70, 25.5, 100/3, 200/3], [80, 36.7, 50.4534, 200/3], [90, 75, 100, 200/3], [100, 0, 1.112, 200/3]],
                                            weights=[50, 0, 10, 40])
    
        # There are 4 assessments in course of id 1
        assessments = Assessment.objects.filter(course_id=course_id)
        for student in students:
            flexes = student.flexassessment_set.filter(assessment__course=course_id)
            flexes.delete() # Delete the predefined flexes in the fixtures
            
        self.bulk_create_flexes_for_student(students[0], assessments, [50, 0, 10, 40]) # This matches the default weights
        self.bulk_create_flexes_for_student(students[1], assessments, [100, None, None, None])
        self.bulk_create_flexes_for_student(students[2], assessments, [60, 20, 10, 10]) # Different from default weights
        self.bulk_create_flexes_for_student(students[3], assessments, [50, 10, 20, 1]) # This doesn't sum to 100
        
        [average_override, average_default, average_difference] = grader.get_averages(groups_dict, course)
        self.assertEqual(average_default, round((84.00 + 20.25 + 27.11 + 66.67) / 4, 2))
        self.assertEqual(average_override, round((84.00 + 20.25 + 40.20 + 66.67) / 4, 2))
        self.assertEqual(average_difference, round((0 + 0 + 13.09 + 0) / 4, 2))
    
    def test_Grader_gets_group_weight_correctly(self):
        course_id = 1
        students = UserProfile.objects.filter(usercourse__role=Roles.STUDENT, usercourse__course__id=course_id)
        student_ids = [str(student.user_id) for student in students]
        
        # Course_id 1 has 4 assignment groups
        groups_dict = self.build_group_dict(student_ids, [[70, 25.5, 100/3, 200/3], [80, 36.7, 50.4534, 200/3], [90, 75, 100, 200/3], [100, 0, 1.112, 200/3]],
                                            weights=[0, 40, 15, 45])
        
        self.assertEqual(grader.get_group_weight(groups_dict, '1'), 0)
        self.assertEqual(grader.get_group_weight(groups_dict, '2'), 40)
        self.assertEqual(grader.get_group_weight(groups_dict, '3'), 15)
        self.assertEqual(grader.get_group_weight(groups_dict, '4'), 45)
        
    def test_Grader_gets_score_correctly(self):
        course_id = 1
        students = UserProfile.objects.filter(usercourse__role=Roles.STUDENT, usercourse__course__id=course_id)
        student_ids = [str(student.user_id) for student in students]
        
        # Course_id 1 has 4 assignment groups
        groups_dict = self.build_group_dict(student_ids, [[70, 25.5, 100/3, 200/3], [80, 36.7, 50.4534, 200/3], [90, 75, 100, 200/3], [100, 0, 1.112, 200/3]],
                                            weights=[0, 40, 15, 45])
        
        self.assertEqual(grader.get_score(groups_dict, 1, students[0]), 70)
        self.assertEqual(grader.get_score(groups_dict, 2, students[1]), 36.7)
        self.assertEqual(grader.get_score(groups_dict, 3, students[2]), 100)
        self.assertEqual(grader.get_score(groups_dict, 4, students[3]), 200/3)
        
        
    


        
        