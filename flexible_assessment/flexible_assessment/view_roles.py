from abc import ABC, abstractmethod
from .models import Roles


class ViewRole(ABC):
    """Abstract base class used for user test function to check role"""

    @property
    @abstractmethod
    def permitted_roles(self):
        pass

    @classmethod
    def permission_test(self, user):
        return user.role in self.permitted_roles


class Instructor(ViewRole):
    permitted_roles = (Roles.ADMIN, Roles.TEACHER, Roles.TA)


class Student(ViewRole):
    permitted_roles = (Roles.STUDENT,)
