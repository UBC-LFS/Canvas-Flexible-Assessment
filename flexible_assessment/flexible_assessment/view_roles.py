from abc import ABC, abstractmethod

from .models import Roles, UserCourse


class ViewRole(ABC):
    """Abstract base class used for user test function to check role"""

    @property
    @abstractmethod
    def permitted_roles(self):
        pass

    @classmethod
    def permission_test(cls, user, course):
        user_course_set = UserCourse.objects.filter(
            user_id=user.user_id, course_id=course.id
        )

        first = user_course_set.first()
        return first.role in cls.permitted_roles if first else False


class Instructor(ViewRole):
    permitted_roles = (Roles.ADMIN, Roles.TEACHER, Roles.TA)


class Student(ViewRole):
    permitted_roles = (Roles.STUDENT,)
