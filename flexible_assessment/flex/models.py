import uuid
from django.db import models

class User(models.Model):
    id = models.IntegerField(primary_key=True)
    role = models.CharField(max_length=75)

# TODO: add flexible assessment deadline date
class Course(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=75)

class UserCourse(models.Model):
    class Meta:
        constraints = [
            models.constraints.UniqueConstraint(fields=['user_id', 'course_id'], name='User and Course unique')
        ]

    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE)

class Assessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=75)
    default = models.FloatField()

class AssessmentCourse(models.Model):
    class Meta:
        constraints = [
            models.constraints.UniqueConstraint(fields=['assessment_id', 'course_id'], name='Assessment and Course unique')
        ]

    assessment_id = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE)

class FlexAssessment(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    assessment_id = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    flex = models.FloatField()

