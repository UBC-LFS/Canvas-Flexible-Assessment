import uuid

from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin)
from django.db import models

# TODO: limit admin perms


class UserProfileManager(BaseUserManager):
    """Extends Base User Manager for creating users and superusers of type UserProfile

    Methods
    -------
    create_user(user_id, login_id, display_name, role, password=None)
        Creates regular user
    create_superuser(user_id, login_id, display_name, role, password=None)
        Creates superuser"""

    def create_user(self, user_id, login_id,
                    display_name, role, password=None):
        """Regular User creation

        Parameters
        ----------
        user_id : int
            Unique id for Canvas user used for identification
        login_id : str
            Used as canvas login/username (CWL)
        display_name : str
            Name of user
        role : int
            Used as identification for role of user in course (see models.Roles class)

        Returns
        -------
        user : UserProfile
            Regular user instance"""

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
        """Superuser creation

        Parameters
        ----------
        user_id : int
            Unique id for Canvas user used for identification
        login_id : str
            Used as canvas login/username (CWL)
        display_name : str
            Name of user
        role : int
            Used as identification for role of user in course (see models.Roles class)

        Returns
        -------
        user : UserProfile
            Superuser instance"""

        user = self.create_user(
            user_id,
            login_id,
            display_name,
            role,
            password=password)
        user.save(using=self._db)
        return user


class Roles(models.IntegerChoices):
    """Role choices available for user mapped to an integer"""
    ADMIN = 1
    TEACHER = 2
    TA = 3
    STUDENT = 4


class UserProfile(AbstractBaseUser, PermissionsMixin):
    """Table containing user entries for Instructor/TA/Student for course or Admin instance

    Attributes
    ----------
    user_id : int
        Unique id for Canvas user used for identification
    login_id : str
        Used as canvas login/username (CWL)
    display_name : str
        Name of user
    role : int
        Used as identification for role of user in course (see models.Roles class)
    objects : UserProfileManager
        Instance of user manager class extending the BaseUserManager
    """

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

    class Meta:
        ordering = ['display_name']


class Course(models.Model):
    """Table for course entries with flexible assessment

    Attributes
    ----------
    id : int
        Unique id for the Canvas course
    title : str
        Title of the course
    open : DateTime
        Open date for students to add or change grade allocation for assessments
    close : DateTime
        Due date for students to add or change grade allocation for assessments
    """

    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=100)
    open = models.DateTimeField(null=True)
    close = models.DateTimeField(null=True)

    def __str__(self):
        return self.title


class UserCourse(models.Model):
    """Table linking users and courses for many-to-many relationship, entries are unique

    Attributes
    ----------
    user : ForeignKey -> UserProfile
        Foreign key with UserProfile
    course : ForeignKey -> Course
        Foreign Key with Course
    """

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


class AssignmentGroup(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Assessment(models.Model):
    """Table of assessment entries

    Attributes
    ----------
    id : uuid
        Assigns random uuid as primary key for assessment identification
    title : str
        Title of assessment
    default : float
        Default grade allocation for assessment given by Instructor
        Should be in [0, 100]
    max : float
        Max grade allocation that can be set by student
        Should be in [0, 100]
    min : float
        Min grade allocation that can be set by student
        Should be in [0, 100]
    course : ForeignKey -> Course
        Foreign Key with Course
    group : ForeignKey -> AssignmentGroup
        Foreign Key with AssignmentGroup
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=100)
    default = models.IntegerField()
    min = models.IntegerField()
    max = models.IntegerField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    group = models.ForeignKey(
        AssignmentGroup,
        on_delete=models.CASCADE,
        null=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["title"]


class FlexAssessment(models.Model):
    """Table containing students grade allocation for assessment
    All assessments for student in a course should total to 100

    Attributes
    ----------
    user : ForeignKey -> UserProfile
        Foreign Key with UserProfile
    assessment : ForeignKey -> Assessment
        Foreign Key with Assessment
    flex : float
        Student's grade allocation for assessment
    """

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    flex = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["assessment__title"]


class UserComment(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    comment = models.TextField(max_length=100, default="", blank=True)
