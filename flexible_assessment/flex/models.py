import uuid

from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin)
from django.db import models


class UserProfileManager(BaseUserManager):
    # TODO: limit admin perms
    def create_user(self, user_id, login_id,
                    display_name, role, password=None):
        user = self.model(
            user_id=user_id,
            login_id=login_id,
            display_name=display_name,
            role=role
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_id, login_id,
                         display_name, role, password=None):
        user = self.create_user(
            user_id,
            login_id,
            display_name,
            role,
            password=password)
        user.save(using=self._db)
        return user


class Roles(models.IntegerChoices):
    ADMIN = 1
    TEACHER = 2
    TA = 3
    STUDENT = 4


class UserProfile(AbstractBaseUser, PermissionsMixin):
    user_id = models.IntegerField(primary_key=True)
    login_id = models.CharField(max_length=100)
    display_name = models.CharField(max_length=255)
    role = models.IntegerField(choices=Roles.choices)

    objects = UserProfileManager()

    USERNAME_FIELD = 'user_id'
    REQUIRED_FIELDS = ['login_id', 'display_name', 'role']

    def __str__(self):
        return self.login_id + ', ' + self.display_name

    @property
    def is_superuser(self):
        return self.role == Roles.ADMIN

    @property
    def is_staff(self):
        return self.role == Roles.ADMIN


# TODO: add flexible assessment deadline date
class Course(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=100)
    availability = models.DateTimeField(null=True)

    def __str__(self):
        return self.title


class UserCourse(models.Model):
    class Meta:
        constraints = [
            models.constraints.UniqueConstraint(
                fields=[
                    'user_id',
                    'course_id'],
                name='User and Course unique')
        ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)


class Assessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=100)
    # add ranges
    default = models.FloatField()
    max = models.FloatField()
    min = models.FloatField()

    def __str__(self):
        return self.title


class AssessmentCourse(models.Model):
    class Meta:
        constraints = [
            models.constraints.UniqueConstraint(
                fields=[
                    'assessment_id',
                    'course_id'],
                name='Assessment and Course unique')
        ]

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)


class FlexAssessment(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    flex = models.FloatField()
