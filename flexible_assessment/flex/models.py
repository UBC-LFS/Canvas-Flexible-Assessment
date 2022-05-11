import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class UserProfileManager(BaseUserManager):
    def create_user(self, user_id, login_id, display_name, role, password=None):
        user = self.model(
            user_id = user_id,
            login_id = login_id,
            display_name = display_name,
            role = role
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_id, login_id, display_name, role, password=None):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        user = self.create_user(user_id, login_id, display_name, role, password=password)
        user.save(using=self._db)
        return user


class UserProfile(AbstractBaseUser):
    user_id = models.IntegerField(unique=True)
    login_id = models.CharField(max_length=100)
    display_name = models.CharField(max_length=255)
    role = models.CharField(max_length=100) # make this choice set

    objects = UserProfileManager()

    USERNAME_FIELD = 'user_id'
    REQUIRED_FIELDS = ['login_id', 'display_name', 'role']

    def __str__(self):
        return self.login_id + ', ' + self.display_name

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, label):
        return True

    @property
    def is_staff(self):
        return 'Account Admin' in self.role

# TODO: add flexible assessment deadline date
class Course(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=100)

    def __str__(self):
        return self.title

class UserCourse(models.Model):
    class Meta:
        constraints = [
            models.constraints.UniqueConstraint(fields=['user_id', 'course_id'], name='User and Course unique')
        ]

    user_id = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE)

class Assessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=100)
    default = models.FloatField()

    def __str__(self):
        return self.title

class AssessmentCourse(models.Model):
    class Meta:
        constraints = [
            models.constraints.UniqueConstraint(fields=['assessment_id', 'course_id'], name='Assessment and Course unique')
        ]

    assessment_id = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE)

class FlexAssessment(models.Model):
    user_id = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    assessment_id = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    flex = models.FloatField()

