import uuid

from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin)
from django.db import models


class UserProfileManager(BaseUserManager):
    """Extends Base User Manager for creating users and superusers
    of type UserProfile

    Methods
    -------
    create_superuser(user_id, login_id, display_name, role, password=None)
        Creates superuser"""

    def create_user(self, user_id, login_id,
                    display_name, superuser=False, password=None):
        """Regular User creation
        Parameters
        ----------
        user_id : int
            Unique id for Canvas user used for identification
        login_id : str
            Used as canvas login/username (CWL)
        display_name : str
            Name of user
        Returns
        -------
        user : UserProfile
            Regular user instance
        """

        user = self.model(
            user_id=user_id,
            login_id=login_id,
            display_name=display_name,
            superuser=superuser
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_id, login_id,
                         display_name, superuser=True, password=None):
        """Superuser creation
        Parameters
        ----------
        user_id : int
            Unique id for Canvas user used for identification
        login_id : str
            Used as canvas login/username (CWL)
        display_name : str
            Name of user
        Returns
        -------
        user : UserProfile
            Superuser instance
        """

        user = self.create_user(
            user_id,
            login_id,
            display_name,
            superuser=superuser,
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
    """Table containing user entries for Instructor/TA/Student for
    course or Admin instance

    Attributes
    ----------
    user_id : int
        Unique id for Canvas user used for identification
    login_id : str
        Used as canvas login/username (CWL)
    display_name : str
        Name of user
    objects : UserProfileManager
        Instance of user manager class extending the BaseUserManager
    """

    user_id = models.IntegerField(primary_key=True)
    login_id = models.CharField(max_length=100, null=True, blank=True)
    display_name = models.CharField(max_length=255)
    superuser = models.BooleanField(default=False)

    objects = UserProfileManager()

    USERNAME_FIELD = 'user_id'
    REQUIRED_FIELDS = ['login_id', 'display_name']

    def __str__(self):
        return '{}, {}'.format(self.login_id, self.display_name)

    @property
    def is_superuser(self):
        return self.superuser

    @property
    def is_staff(self):
        return self.superuser 

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
        Open date for students to add or
        change grade allocation for assessments
    close : DateTime
        Due date for students to add or
        change grade allocation for assessments
    welcome_instructions: Textfield
        Displays for students at the top of Assessments page
    comment_instructions: Textfield
        Displays for students before their comment box
    """

    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=100)
    open = models.DateTimeField(null=True)
    close = models.DateTimeField(null=True)
    welcome_instructions = models.TextField(blank=True, null=True)
    comment_instructions = models.TextField(blank=True, null=True)

    def __str__(self):
        return "{} - {}".format(self.title, self.id)

    def set_flex_assessments(self, assessment):
        """Creates flex assessment objects for new assessments in the course"""

        user_courses = self.usercourse_set.filter(
            role=Roles.STUDENT).select_related('user')
        users = [user_course.user for user_course in user_courses]
        flex_assessments = [
            FlexAssessment(user=user, assessment=assessment)
            for user in users
            if not FlexAssessment.objects.filter(
                user=user, assessment=assessment).exists()]
        FlexAssessment.objects.bulk_create(flex_assessments)

    def reset_students(self, students):
        """Resets flex allocations and comments for students"""

        for student in students:
            fas_to_reset = student.flexassessment_set \
                .filter(assessment__course=self)
            fas_to_reset.update(flex=None)
            student.usercomment_set.filter(course=self).update(comment="")

    def reset_all_students(self):
        """Resets flex allocations for all students in the course"""

        fas_to_reset = FlexAssessment.objects.filter(assessment__course=self)
        fas_to_reset.update(flex=None)

        comments_to_reset = UserComment.objects.filter(course=self)
        comments_to_reset.update(comment="")


class UserCourse(models.Model):
    """Table linking users and courses for many-to-many relationship,
    entries are unique

    Attributes
    ----------
    user : ForeignKey -> UserProfile
        Foreign key with UserProfile
    course : ForeignKey -> Course
        Foreign Key with Course
    role : int
        Used as identification for role of user in course
        (see models.Roles class)
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
    role = models.IntegerField(choices=Roles.choices)

    def __str__(self):
        return '{}, {}, {}'.format(self.user.display_name, self.course.title, self.role)


class Assessment(models.Model):
    """Table of assessment entries

    Attributes
    ----------
    id : uuid
        Assigns random uuid as primary key for assessment identification
    title : str
        Title of assessment
    default : decimal (2 decimal places)
        Default grade allocation for assessment given by Instructor
        Should be in [0, 100]
    max : decimal (2 decimal places)
        Max grade allocation that can be set by student
        Should be in [0, 100]
    min : decimal (2 decimal places)
        Min grade allocation that can be set by student
        Should be in [0, 100]
    course : ForeignKey -> Course
        Foreign Key with Course
    group : int
        Canvas assignment group id
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=100)
    default = models.DecimalField(max_digits=5, decimal_places=2)
    min = models.DecimalField(max_digits=5, decimal_places=2)
    max = models.DecimalField(max_digits=5, decimal_places=2)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    group = models.IntegerField(null=True)

    def __str__(self):
        return '{}, {}'.format(self.title, self.course.title)

    def check_valid_flex(self):
        """Returns students with flex allocations
        out of allowed assessment range i.e. have conflicts
        """

        flex_assessments = self.flexassessment_set.exclude(flex__isnull=True)

        conflict_fas = flex_assessments.filter(flex__lt=self.min) \
            | flex_assessments.filter(flex__gt=self.max)
        conflict_fas = conflict_fas.select_related('user')

        conflict_students = {fa.user for fa in conflict_fas}

        return conflict_students


class FlexAssessment(models.Model):
    """Table containing students grade allocation for assessment
    All assessments for student in a course should total to 100

    Attributes
    ----------
    user : ForeignKey -> UserProfile
        Foreign Key with UserProfile
    assessment : ForeignKey -> Assessment
        Foreign Key with Assessment
    flex : decimal (2 decimal places)
        Student's grade allocation for assessment
        Should be in [0.00, 100.00]
    """

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    flex = models.DecimalField(null=True, blank=True, max_digits=5, decimal_places=2)

    def __str__(self):
        return '{}, {}'.format(self.user.display_name, self.assessment.title)


class UserComment(models.Model):
    """Table containing students comment for grade allocation in the course

    Attributes
    ----------
    user : ForeignKey -> UserProfile
        Foreign Key with UserProfile
    course : ForeignKey -> Course
        Foreign Key with Course
    comment : str
        Student's comment for the course
    """

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    comment = models.TextField(max_length=100, default="", blank=True)

    def __str__(self):
        return '{}, {} comment'.format(self.user.display_name,
                                       self.course.title)
